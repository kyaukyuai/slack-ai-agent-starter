import datetime
import json
import math
import random
import re

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from slack_ai_agent.agents.configuration import Configuration

from .models import ReportState
from .utils import get_config_value


def compile_final_report(state: ReportState, config: RunnableConfig):
    """Compile the final report in the specified JSON format"""
    # Get sections
    sections = state["sections"]
    completed_sections = {s.headline: s.content for s in state["completed_sections"]}
    url = state["input"].url

    # Update sections with completed content while maintaining original order
    for section in sections:
        content = completed_sections.get(section.headline, "")
        print(f"Processing section: {section.headline}")
        print(f"Content type: {type(content)}")
        print(f"Content preview: {content[:100]}...")

        # JSONが含まれているかチェック
        if "```json" in content and "```" in content:
            # JSONブロックを抽出
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                print(f"Extracted JSON: {json_str[:100]}...")
                try:
                    # JSONを解析
                    content_json = json.loads(json_str)
                    print(f"Parsed JSON keys: {list(content_json.keys())}")

                    # contentフィールドを取得
                    if isinstance(content_json, dict) and "content" in content_json:
                        # 実際のコンテンツを設定
                        section.content = content_json.get("content", "")
                        print(f"Set content: {section.content[:100]}...")

                        # quotesとreferencesも更新
                        if "quotes" in content_json:
                            # 引用を構造化
                            quotes = []
                            for quote in content_json.get("quotes", []):
                                if isinstance(quote, dict):
                                    # すでに構造化されている場合
                                    quotes.append(quote)
                                elif isinstance(quote, str):
                                    # 文字列の場合は構造化
                                    quotes.append(
                                        {"text": quote, "source": "", "relevance": 0.5}
                                    )
                            section.quotes = quotes
                            print(f"Set {len(quotes)} quotes")

                        if "references" in content_json:
                            section.references = content_json.get("references", [])
                            print(f"Set {len(section.references)} references")
                    else:
                        print("No 'content' field found in JSON or not a dict")
                        section.content = content
                except json.JSONDecodeError as e:
                    print(f"JSONの解析に失敗しました: {e}")
                    # JSONの解析に失敗した場合は、そのままのコンテンツを使用
                    section.content = content
            else:
                print("JSON block not found in content")
                # JSONブロックが見つからない場合
                section.content = content
        else:
            print("No JSON markers found in content")
            # JSONでない場合はそのままのコンテンツを使用
            section.content = content

    # Compile full content
    full_content = "\n\n".join([s.content for s in sections])

    # LLMを使って魅力的なタイトルを生成
    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # LLMを使用して要約を生成
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(
        model=writer_model_name, model_provider=writer_provider, temperature=0.7
    )

    # 基本情報を取得
    base_title = ""
    if sections and sections[0].headline:
        base_title = sections[0].headline
    else:
        base_title = state["input"].title
        if not base_title:
            markdown = state["input"].markdown
            first_line = markdown.split("\n", 1)[0].strip() if markdown else ""
            base_title = first_line if first_line else "URLコンテンツの分析"

    # タイトル生成プロンプト
    title_prompt = (
        "あなたは魅力的な見出しを作成するプロの編集者です。\n"
        "以下の記事内容と基本タイトルから、読者の興味を引く魅力的なタイトルを1つ作成してください。\n"
        "タイトルは40文字以内で、記事の価値や重要性が伝わるものにしてください。\n"
        f"基本タイトル: {base_title}\n"
        f"記事内容: {full_content}\n"
    )

    title_response = writer_model.invoke([HumanMessage(content=title_prompt)])
    title = str(title_response.content).strip()

    # タイトルが長すぎる場合は切り詰める
    if len(title) > 40:
        title = title[:37] + "..."

    # 重要度計算（0.7-0.95）
    importance = round(random.uniform(0.7, 0.95), 2)

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # LLMを使用して要約を生成
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(
        model=writer_model_name, model_provider=writer_provider, temperature=0
    )

    # Generate micro summary (60-80 characters)
    micro_prompt = (
        "あなたは上級編集者です。\n"
        "以下の記事本文を60～80字の1文で要約してください。\n"
        f"記事: {full_content}"
    )

    micro_response = writer_model.invoke([HumanMessage(content=micro_prompt)])
    micro = str(micro_response.content).strip()

    # Ensure micro is within 60-80 characters
    if len(micro) < 60:
        micro += "..." + " " * (60 - len(micro) - 3)
    elif len(micro) > 80:
        micro = micro[:77] + "..."

    # Generate digest (3行要約)
    digest_prompt = (
        "以下の記事を3行で要約し、日本語50字以内/行で出力。\n"
        "返却形式:\n"
        "1) 行1\n"
        "2) 行2\n"
        "3) 行3\n"
        f"記事: {full_content}"
    )

    digest_response = writer_model.invoke([HumanMessage(content=digest_prompt)])
    digest_text = str(digest_response.content).strip()

    # 行を抽出
    digest = []
    for line in digest_text.split("\n"):
        line = line.strip()
        if line and not line.startswith("返却形式:"):
            # 番号や記号を削除
            clean_line = line.lstrip("0123456789.) ")
            if clean_line:
                digest.append(clean_line)

    # 3行になるよう調整
    while len(digest) < 3:
        digest.append("詳細はレポート本文をご覧ください。")
    digest = digest[:3]

    # 各行が50字以内になるよう調整
    for i in range(len(digest)):
        if len(digest[i]) > 50:
            digest[i] = digest[i][:47] + "..."

    # Generate tags (5-10 tags)
    tags_prompt = (
        "あなたはコンテンツ分類の専門家です。\n"
        "以下の記事内容から、1〜3個のタグを抽出してください。\n"
        "タグは記事の主要なトピック、キーワード、カテゴリを表すものにしてください。\n"
        "各タグは1〜3単語の日本語で、カンマ区切りで出力してください。\n"
        f"記事タイトル: {title}\n"
        f"記事内容: {full_content}\n"
    )

    tags_response = writer_model.invoke([HumanMessage(content=tags_prompt)])
    tags_text = str(tags_response.content).strip()

    # タグをリストに変換
    tags: list[str] = []
    for tag in tags_text.split(","):
        tag = tag.strip()
        if tag and len(tags) < 10:  # 最大10個まで
            tags.append(tag)

    # タグが少なすぎる場合の対応
    if len(tags) < 5:
        # セクションの見出しからタグを追加
        for section in sections:
            if section.headline and section.headline not in tags and len(tags) < 10:
                tags.append(section.headline)

    # Calculate estimated reading time in minutes
    # Assuming average reading speed of 200 characters per minute
    char_count = len(full_content)
    estimated_minutes = max(1, math.ceil(char_count / 200))

    # Create timestamp
    created_at = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Create the JSON structure
    # 設計書に合わせた構造で出力（input.markdownを除外）
    report_json = {
        "input": {
            "url": url,
            "title": state["input"].title,
            "metadata": state["input"].metadata,
        },
        "title": title,
        "image_url": "",  # 画像URLは空で初期化
        "micro": micro,
        "digest": digest,
        "tags": tags,  # タグを追加
        "importance": importance,
        "sections": [
            {
                "headline": s.headline,
                "content": s.content,
                "quotes": s.quotes,
                "references": s.references,
            }
            for s in sections
        ],
        "readState": "unread",
        "estimatedMinutes": estimated_minutes,
        "createdAt": created_at,
    }

    # Convert to JSON string
    report_json_str = json.dumps(report_json, ensure_ascii=False, indent=2)

    # ReportState["title"]にもセット
    return {"final_report": report_json_str, "title": title}
