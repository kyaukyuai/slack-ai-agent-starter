import json
import os

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command
from openai import OpenAI

from slack_ai_agent.agents.configuration import Configuration
from slack_ai_agent.agents.prompts.deep_research_final_section_writer_instructions import (
    final_section_writer_instructions,
)
from slack_ai_agent.agents.prompts.deep_research_section_grader_instructions import (
    section_grader_instructions,
)
from slack_ai_agent.agents.prompts.deep_research_section_writer_instructions import (
    section_writer_instructions,
)

from .models import ReportState
from .models import SearchQuery
from .models import SectionState
from .utils import extract_json_from_response
from .utils import parse_json_with_fallback


def write_section(state: SectionState, config: RunnableConfig) -> Command:
    """Write a section of the report with structured output"""
    # Get state
    url = state["url"]
    url_content = state["url_content"]
    markdown = url_content if isinstance(url_content, str) else str(url_content)
    section = state["section"]
    source_str = state["source_str"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Format system instructions
    system_instructions = section_writer_instructions.format(
        topic=f"Content from URL: {url}",
        section_title=section.headline,
        section_topic=section.description,
        context=f"URL Content:\n{markdown}...\n\nAdditional Research:\n{source_str}",
        section_content=section.content,
    )
    # 元のプロンプトに従って、マークダウン形式での出力を指示
    system_instructions += """
あなたは優秀なテクニカルライターです。以下の要件に従い、レポートのセクションをJSON形式で生成してください。本文はすべて日本語とします。

### 出力形式
単一のJSON オブジェクトで、以下のプロパティを含みます:
- headline (string): セクションのタイトル
- content (string): 本文
- quotes (array): 関連する重要な引用
- references (array): 参照情報源

### 各プロパティの詳細要件

【headline（見出し）】
- 日本語で40字以内
- 具体的かつ簡潔に
- 記号、絵文字、強調などの装飾は使用しない
- 見出しはheadlineプロパティにのみ含め、content内には含めない

【content（本文）】
- 全体で300〜400文字以内
- 最初の文（80字以内）で最も重要な洞察を述べる
- 続けて2〜3文の短い段落を記述
- URLは直接記載せず、referencesで参照

【quotes（引用）】
- 正確に3件の引用（3件未満または4件以上は不可）
- 各引用は以下の形式:
```
{
"text": "引用文（80字以内）",
"source": "出典（例: レポート名、記事タイトルなど）",
"url": "参照元のURL（完全な形式）",
}
```

【references（参照）】
- 1〜3件の参照情報源
- 各参照は以下の形式:
```
{
"title": "参照タイトル（80字以内）",
"url": "参照元のURL（完全な形式）",
"metadata": {
"author": "著者名（判明している場合のみ）",
"publishedDate": "発行日（YYYY-MM-DD形式、判明している場合のみ）"
}
}
```

### 品質基準
- 事実の正確性: 検証可能な情報に基づくこと
- 論理的一貫性: 前後の文脈が矛盾なく繋がること
- 簡潔性: 余分な説明や繰り返しを避けること
- 客観性: 特定の視点に偏らない記述

### 注意事項
- 指示文や説明は出力に含めない
- 不明な情報は推測せず省略する
- 文字数制限は厳守する
- 本文、引用、参照は相互に整合性のあるものにする
"""

    # Generate section

    # Function callingのためのスキーマを定義
    function_schema = {
        "name": "generate_section",
        "description": "Generate a section of a report with content, quotes, and references",
        "parameters": {
            "type": "object",
            "properties": {
                "headline": {
                    "type": "string",
                    "description": "セクションのタイトル（日本語で40字以内、装飾なし、マークダウン記法「# 」などは使用しない）",
                },
                "content": {
                    "type": "string",
                    "description": "本文（日本語で200〜300文字以内、最初の文で重要な洞察を述べる）",
                },
                "quotes": {
                    "type": "array",
                    "description": "関連する重要な引用（正確に3件）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "引用文（80字以内）",
                            },
                            "source": {
                                "type": "string",
                                "description": "出典（例: レポート名、記事タイトルなど）",
                            },
                            "url": {
                                "type": "string",
                                "description": "参照元のURL（完全な形式）",
                            },
                        },
                        "required": ["text", "source", "url"],
                    },
                },
                "references": {
                    "type": "array",
                    "description": "参照情報源（1〜3件）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "参照タイトル（80字以内）",
                            },
                            "url": {
                                "type": "string",
                                "description": "参照元のURL（完全な形式）",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "参照に関する追加メタデータ",
                                "properties": {
                                    "author": {
                                        "type": "string",
                                        "description": "著者名（判明している場合のみ）",
                                    },
                                    "publishedDate": {
                                        "type": "string",
                                        "description": "発行日（YYYY-MM-DD形式、判明している場合のみ）",
                                    },
                                },
                            },
                        },
                        "required": ["title", "url"],
                    },
                },
            },
            "required": ["headline", "content", "quotes", "references"],
        },
    }

    # OpenAI APIクライアントを初期化
    try:
        print("Invoking OpenAI API for section writing with function calling...")

        # OpenAI APIクライアントを初期化
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # Function callingを実行
        response = client.chat.completions.create(  # type: ignore[call-overload]
            model="gpt-4o-mini",
            temperature=0,
            max_completion_tokens=32_768,
            messages=[
                {"role": "system", "content": system_instructions},
                {
                    "role": "user",
                    "content": "提供されたURLコンテンツと追加ソースに基づいて、日本語でレポートセクションを生成してください。",
                },
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": function_schema["name"],
                        "description": function_schema["description"],
                        "parameters": function_schema["parameters"],
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": "generate_section"}},
        )

        # 関数呼び出し結果を取得
        if (
            hasattr(response.choices[0].message, "tool_calls")
            and response.choices[0].message.tool_calls
        ):
            # 関数呼び出しの引数を解析
            tool_call = response.choices[0].message.tool_calls[0]
            section_output = json.loads(tool_call.function.arguments)

            # 結果をセクションに設定
            section.content = section_output.get("content", "")
            section.quotes = section_output.get("quotes", [])
            section.references = section_output.get("references", [])

            print("Successfully extracted structured output:")
            print(f"- Content length: {len(section.content)} chars")
            print(f"- Quotes: {len(section.quotes)} items")
            print(f"- References: {len(section.references)} items")
        else:
            # Function callingが失敗した場合のフォールバック
            print("Function calling failed, falling back to text extraction")

            # 通常の呼び出しを実行
            fallback_response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": system_instructions},
                    {
                        "role": "user",
                        "content": "提供されたURLコンテンツと追加ソースに基づいて、日本語でレポートセクションを生成してください。マークダウン形式で出力し、最後にJSON形式でも提供してください。",
                    },
                ],
            )

            response_text = fallback_response.choices[0].message.content or ""

            # JSONを抽出
            json_str = extract_json_from_response(response_text)

            # JSONを解析
            section_output = (
                parse_json_with_fallback(
                    json_str, {"content": "", "quotes": [], "references": []}
                )
                or {}
            )

            # セクションに設定
            if section_output and isinstance(section_output, dict):
                section.content = section_output.get("content", "")
                section.quotes = section_output.get("quotes", [])
                section.references = section_output.get("references", [])
            else:
                # JSONの解析に失敗した場合
                section.content = (
                    response_text.split("```json")[0].strip()
                    if response_text and "```json" in response_text
                    else response_text or ""
                )
                section.quotes = []
                section.references = []
    except Exception as e:
        print(f"Error in section writing: {str(e)}")
        # エラーが発生した場合、安全に処理
        try:
            response_text = (
                str(response.choices[0].message.content)
                if hasattr(response.choices[0].message, "content")
                else str(response)
            )
        except NameError:
            # responseが定義されていない場合
            response_text = f"エラーが発生しました: {str(e)}"
        section.content = response_text
        section.quotes = []
        section.references = []

    # Grade prompt
    section_grader_instructions_formatted = section_grader_instructions.format(
        topic=f"Content from URL: {url}",
        section_topic=section.description,
        section=section.content,
    )

    # JSON形式で出力するようにプロンプトを設定
    section_grader_instructions_formatted += """
重要: 以下のJSON形式で出力してください：

```json
{
  "grade": "pass",
  "follow_up_queries": [
    {"search_query": "追加の検索クエリ1"},
    {"search_query": "追加の検索クエリ2"}
  ]
}
```

gradeは "pass" または "fail" のいずれかを指定してください。
必ず有効なJSONを出力してください。
"""

    # Function callingのためのスキーマを定義
    feedback_function_schema = {
        "name": "grade_section",
        "description": "Grade the section and provide follow-up queries if needed",
        "parameters": {
            "type": "object",
            "properties": {
                "grade": {
                    "type": "string",
                    "enum": ["pass", "fail"],
                    "description": "Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail').",
                },
                "follow_up_queries": {
                    "type": "array",
                    "description": "List of follow-up search queries if grade is 'fail'",
                    "items": {
                        "type": "object",
                        "properties": {
                            "search_query": {
                                "type": "string",
                                "description": "A search query for additional information",
                            }
                        },
                        "required": ["search_query"],
                    },
                },
            },
            "required": ["grade"],
        },
    }

    try:
        # OpenAI APIクライアントを初期化
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # Function callingを実行
        response = client.chat.completions.create(  # type: ignore[call-overload]
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": section_grader_instructions_formatted},
                {
                    "role": "user",
                    "content": "Grade the report and consider follow-up questions for missing information:",
                },
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": feedback_function_schema["name"],
                        "description": feedback_function_schema["description"],
                        "parameters": feedback_function_schema["parameters"],
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": "grade_section"}},
        )

        # 関数呼び出し結果を取得
        if (
            hasattr(response.choices[0].message, "tool_calls")
            and response.choices[0].message.tool_calls
        ):
            # 関数呼び出しの引数を解析
            tool_call = response.choices[0].message.tool_calls[0]
            feedback_dict = json.loads(tool_call.function.arguments)

            # 結果を取得
            grade = feedback_dict.get("grade", "fail")
            follow_up_queries_data = feedback_dict.get("follow_up_queries", [])

            # SearchQueryオブジェクトに変換
            follow_up_queries = []
            for query_dict in follow_up_queries_data:
                follow_up_queries.append(
                    SearchQuery(search_query=query_dict.get("search_query", ""))
                )

            print(f"Successfully extracted grading result: {grade}")
            print(f"Follow-up queries: {len(follow_up_queries)} items")
        else:
            # Function callingが失敗した場合のフォールバック
            print(
                "Function calling for grading failed, falling back to text extraction"
            )

            # 通常の呼び出しを実行
            fallback_response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": section_grader_instructions_formatted,
                    },
                    {
                        "role": "user",
                        "content": "Grade the report and consider follow-up questions for missing information:",
                    },
                ],
            )

            response_text = fallback_response.choices[0].message.content or ""

            # JSONを抽出
            json_str = extract_json_from_response(response_text)

            # JSONを解析
            feedback_dict = (
                parse_json_with_fallback(
                    json_str, {"grade": "fail", "follow_up_queries": []}
                )
                or {}
            )
            grade = (
                feedback_dict.get("grade", "fail")
                if isinstance(feedback_dict, dict)
                else "fail"
            )

            # SearchQueryオブジェクトに変換
            follow_up_queries = []
            if isinstance(feedback_dict, dict):
                for query_dict in feedback_dict.get("follow_up_queries", []):
                    if isinstance(query_dict, dict):
                        follow_up_queries.append(
                            SearchQuery(search_query=query_dict.get("search_query", ""))
                        )
    except Exception as e:
        print(f"Error in section grading: {str(e)}")
        grade = "fail"
        follow_up_queries = [SearchQuery(search_query=f"エラー: {str(e)}")]

    if not follow_up_queries and grade == "fail":
        # デフォルト値を設定
        follow_up_queries = [
            SearchQuery(search_query="エラー: JSONの解析に失敗しました")
        ]

    if grade == "pass" or state["search_iterations"] >= configurable.max_search_depth:
        # Publish the section to completed sections
        return Command(update={"completed_sections": [section]}, goto=END)
    else:
        # Update the existing section with new content and update search queries
        return Command(
            update={"search_queries": follow_up_queries, "section": section},
            goto="search_web",
        )


def write_final_sections(state: SectionState, config: RunnableConfig):
    """Write final sections of the report with structured output"""
    # Get state
    url = state["url"]
    url_content = state["url_content"]
    markdown = url_content if isinstance(url_content, str) else str(url_content)
    section = state["section"]
    completed_report_sections = state["report_sections_from_research"]

    # Format system instructions
    system_instructions = final_section_writer_instructions.format(
        topic=f"Content from URL: {url}",
        section_title=section.headline,
        section_topic=section.description,
        context=f"URL Content:\n{markdown[:3000]}...\n\nCompleted Sections:\n{completed_report_sections}",
    )
    # 元のプロンプトに従って、マークダウン形式での出力を指示
    system_instructions += """
あなたは優秀なテクニカルライターです。以下の要件に従い、レポートのセクションをJSON形式で生成してください。本文はすべて日本語とします。

### 出力形式
単一のJSON オブジェクトで、以下のプロパティを含みます:
- headline (string): セクションのタイトル
- content (string): 本文
- quotes (array): 関連する重要な引用
- references (array): 参照情報源

### 各プロパティの詳細要件

【headline（見出し）】
- 日本語で40字以内
- 具体的かつ簡潔に
- 記号、絵文字、強調などの装飾は使用しない
- マークダウン記法（"# "など）は絶対に使用しない
- 見出しはheadlineプロパティにのみ含め、content内には含めない
- 先頭に空白や特殊文字を入れない

【content（本文）】
- 全体で200〜300文字以内
- 最初の文（80字以内）で最も重要な洞察を述べる
- 続けて2〜3文の短い段落を記述
- URLは直接記載せず、referencesで参照

【quotes（引用）】
- 正確に3件の引用（3件未満または4件以上は不可）
- 各引用は以下の形式:
```
{
"text": "引用文（80字以内）",
"source": "出典（例: レポート名、記事タイトルなど）",
"url": "参照元のURL（完全な形式）",
}
```

【references（参照）】
- 1〜3件の参照情報源
- 各参照は以下の形式:
```
{
"title": "参照タイトル（80字以内）",
"url": "参照元のURL（完全な形式）",
"metadata": {
"author": "著者名（判明している場合のみ）",
"publishedDate": "発行日（YYYY-MM-DD形式、判明している場合のみ）"
}
}
```

### 品質基準
- 事実の正確性: 検証可能な情報に基づくこと
- 論理的一貫性: 前後の文脈が矛盾なく繋がること
- 簡潔性: 余分な説明や繰り返しを避けること
- 客観性: 特定の視点に偏らない記述

### 注意事項
- 指示文や説明は出力に含めない
- 不明な情報は推測せず省略する
- 文字数制限は厳守する
- 本文、引用、参照は相互に整合性のあるものにする
"""

    # Function callingのためのスキーマを定義
    function_schema = {
        "name": "generate_final_section",
        "description": "Generate a final section of a report with content, quotes, and references",
        "parameters": {
            "type": "object",
            "properties": {
                "headline": {
                    "type": "string",
                    "description": "セクションのタイトル（日本語で40字以内、装飾なし、マークダウン記法「# 」などは使用しない）",
                },
                "content": {
                    "type": "string",
                    "description": "本文（日本語で200〜300文字以内、最初の文で重要な洞察を述べる）",
                },
                "quotes": {
                    "type": "array",
                    "description": "関連する重要な引用（正確に3件）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "引用文（80字以内）",
                            },
                            "source": {
                                "type": "string",
                                "description": "出典（例: レポート名、記事タイトルなど）",
                            },
                            "url": {
                                "type": "string",
                                "description": "参照元のURL（完全な形式）",
                            },
                        },
                        "required": ["text", "source", "url"],
                    },
                },
                "references": {
                    "type": "array",
                    "description": "参照情報源（1〜3件）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "参照タイトル（80字以内）",
                            },
                            "url": {
                                "type": "string",
                                "description": "参照元のURL（完全な形式）",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "参照に関する追加メタデータ",
                                "properties": {
                                    "author": {
                                        "type": "string",
                                        "description": "著者名（判明している場合のみ）",
                                    },
                                    "publishedDate": {
                                        "type": "string",
                                        "description": "発行日（YYYY-MM-DD形式、判明している場合のみ）",
                                    },
                                },
                            },
                        },
                        "required": ["title", "url"],
                    },
                },
            },
            "required": ["headline", "content", "quotes", "references"],
        },
    }

    # Generate section

    # Function callingを使用して構造化出力を取得
    try:
        print("Invoking OpenAI API for final section writing with function calling...")

        # OpenAI APIクライアントを初期化
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # Function callingを実行
        response = client.chat.completions.create(  # type: ignore[call-overload]
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": system_instructions},
                {
                    "role": "user",
                    "content": "提供されたURLコンテンツと完成したセクションに基づいて、日本語でレポートセクションを生成してください。",
                },
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": function_schema["name"],
                        "description": function_schema["description"],
                        "parameters": function_schema["parameters"],
                    },
                }
            ],
            tool_choice={
                "type": "function",
                "function": {"name": "generate_final_section"},
            },
        )

        # 関数呼び出し結果を取得
        if (
            hasattr(response.choices[0].message, "tool_calls")
            and response.choices[0].message.tool_calls
        ):
            # 関数呼び出しの引数を解析
            tool_call = response.choices[0].message.tool_calls[0]
            section_output = json.loads(tool_call.function.arguments)

            # 結果をセクションに設定
            section.content = section_output.get("content", "")
            section.quotes = section_output.get("quotes", [])
            section.references = section_output.get("references", [])

            print("Successfully extracted structured output for final section:")
            print(f"- Content length: {len(section.content)} chars")
            print(f"- Quotes: {len(section.quotes)} items")
            print(f"- References: {len(section.references)} items")
        else:
            # Function callingが失敗した場合のフォールバック
            print(
                "Function calling failed for final section, falling back to text extraction"
            )

            # 通常の呼び出しを実行
            fallback_response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": system_instructions},
                    {
                        "role": "user",
                        "content": "提供されたURLコンテンツと完成したセクションに基づいて、日本語でレポートセクションを生成してください。マークダウン形式で出力し、最後にJSON形式でも提供してください。",
                    },
                ],
            )

            response_text = fallback_response.choices[0].message.content or ""

            # JSONを抽出
            json_str = extract_json_from_response(response_text)

            # JSONを解析
            section_output = (
                parse_json_with_fallback(
                    json_str, {"content": "", "quotes": [], "references": []}
                )
                or {}
            )

            # セクションに設定
            if section_output and isinstance(section_output, dict):
                section.content = section_output.get("content", "")
                section.quotes = section_output.get("quotes", [])
                section.references = section_output.get("references", [])
            else:
                # JSONの解析に失敗した場合
                section.content = (
                    response_text.split("```json")[0].strip()
                    if response_text and "```json" in response_text
                    else response_text or ""
                )
                section.quotes = []
                section.references = []
    except Exception as e:
        print(f"Error in final section writing: {str(e)}")
        # エラーが発生した場合、安全に処理
        try:
            response_text = (
                str(response.choices[0].message.content)
                if hasattr(response.choices[0].message, "content")
                else str(response)
            )
        except NameError:
            # responseが定義されていない場合
            response_text = f"エラーが発生しました: {str(e)}"
        section.content = response_text
        section.quotes = []
        section.references = []

    # Write the updated section to completed sections
    return {"completed_sections": [section]}


def gather_completed_sections(state: ReportState):
    """Gather completed sections from research and format them as context for writing the final sections"""
    # List of completed sections
    completed_sections = state["completed_sections"]

    # Format completed section to str to use as context for final sections
    from .utils import format_sections

    completed_report_sections = format_sections(completed_sections)

    return {"report_sections_from_research": completed_report_sections}
