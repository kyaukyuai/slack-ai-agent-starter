"""Slack app mention event handler module.

This module implements the handler for app_mention events in Slack,
processing mentions using an AI agent and responding back to the channel.
"""

import logging
import os
import re
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from dotenv import load_dotenv
from langgraph_sdk import get_sync_client
from slack_bolt import App


# Set up logging
logger = logging.getLogger(__name__)


load_dotenv()


def format_for_slack_display(text: str) -> str:
    """Markdownテキストを Slack 表示用に変換する.

    Args:
        text: 変換対象のテキスト

    Returns:
        str: Slack表示用に変換されたテキスト
    """
    # 見出し（#）の処理
    text = re.sub(r"#+ (.+?)(?:\n|$)", r"*\1*\n", text)

    # 箇条書きを見やすく変換
    text = re.sub(r"^\s*[-*]\s", "• ", text, flags=re.MULTILINE)

    # 太字の処理 (**text** -> *text*)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

    # コードブロックの処理
    text = re.sub(r"```(\w+)\n", "```\n", text)

    # 段落間の改行を適切に
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 箇条書きの前後に改行を入れて見やすく
    text = re.sub(r"(?<!\n)\n•", "\n\n•", text)

    return text


def extract_text_from_blocks(blocks: List[Dict[str, Any]]) -> str:
    """Slack メッセージの blocks から text を抽出する.

    Args:
        blocks: Slackメッセージのブロック

    Returns:
        str: 抽出されたテキスト
    """
    texts = []
    for block in blocks:
        if block.get("type") == "rich_text":
            for element in block.get("elements", []):
                for rich_text in element.get("elements", []):
                    if text := rich_text.get("text", ""):
                        texts.append(text)
        elif "text" in block:
            if isinstance(block["text"], str):
                texts.append(block["text"])
            elif isinstance(block["text"], dict) and "text" in block["text"]:
                texts.append(block["text"]["text"])
    return " ".join(texts)


def execute_langgraph(
    question: str,
    say: Any,
    user: str,
    thread_ts: Optional[str] = None,
    thread_messages: Optional[Union[Dict[str, Any], Any]] = None,
    app: Optional[App] = None,
    langgraph_url: Optional[str] = None,
    langgraph_token: Optional[str] = None,
) -> Optional[str]:
    """LangGraph を実行してレスポンスを生成する.

    Args:
        question: 質問テキスト
        say: Slackメッセージ送信用の関数
        user: ユーザーID
        thread_ts: スレッドのタイムスタンプ
        thread_messages: スレッドのメッセージ履歴
        app: Slack Bolt アプリケーションインスタンス
        langgraph_url: LangGraph APIのURL
        langgraph_token: LangGraph APIのトークン

    Returns:
        Optional[str]: 生成されたレスポンス
    """
    if not langgraph_url or not langgraph_token:
        logger.error("LANGGRAPH_URL or LANGGRAPH_TOKEN is not set")
        return None

    try:
        client = get_sync_client(
            url=langgraph_url,
            headers={"Authorization": f"Bearer {langgraph_token}"},
        )
        thread = client.threads.create()
        logger.info(f"Created thread: {thread}")

        final_answer = ""
        last_update = time.time()
        last_post_text = ""
        message = None
        formatted_text = ""

        # 会話履歴の構築
        messages = []
        if thread_messages and "messages" in thread_messages:
            for msg in thread_messages["messages"]:
                message_text = msg.get("text", "")

                # blocks からテキストを抽出
                if "blocks" in msg:
                    blocks_text = extract_text_from_blocks(msg["blocks"])
                    if blocks_text:
                        message_text = f"{message_text} {blocks_text}".strip()

                # ボットのメンション部分を除去
                cleaned_text = re.sub(r"<@[A-Z0-9]+>\s*", "", message_text).strip()
                if cleaned_text:
                    messages.append(
                        {
                            "role": "assistant" if msg.get("bot_id") else "user",
                            "content": cleaned_text,
                        }
                    )

        # 現在の質問を追加
        messages.append({"role": "user", "content": question})

        for chunk in client.runs.stream(
            thread["thread_id"],
            assistant_id="agent",
            input={"messages": messages},
            stream_mode="events",
        ):
            if chunk.data.get("event") == "on_chat_model_stream":
                content = chunk.data.get("data", {}).get("chunk", {}).get("content", [])
                if content and len(content) > 0:
                    text = content[0].get("text", "")
                    if text:
                        final_answer += text
                        formatted_text = format_for_slack_display(final_answer)

                        try:
                            # 初回のメッセージ投稿
                            if not message:
                                message = say(
                                    text=f"<@{user}>\n{formatted_text}",
                                    thread_ts=thread_ts,
                                )
                            # 0.3秒以上経過していたら更新
                            elif app and (time.time() - last_update) > 0.3:
                                last_update = time.time()
                                last_post_text = formatted_text
                                app.client.chat_update(
                                    channel=message["channel"],
                                    ts=message["ts"],
                                    text=f"<@{user}>\n{formatted_text}",
                                )
                        except Exception as e:
                            logger.error(f"Error updating message: {e}")

        # 最終更新
        if message and app and last_post_text != formatted_text:
            try:
                app.client.chat_update(
                    channel=message["channel"],
                    ts=message["ts"],
                    text=f"<@{user}>\n{formatted_text}",
                )
            except Exception as e:
                logger.error(f"Error in final update: {e}")

        return final_answer

    except Exception as e:
        logger.error(f"Error in execute_langgraph: {e}")
        return None


def setup_app_mention_handlers(app: App) -> None:
    """Slack botのメンションハンドラーを設定する.

    Args:
        app: Slack Bolt アプリケーションインスタンス
    """

    @app.event("app_mention")
    def handle_app_mention(event: Dict[str, Any], say: Any) -> None:
        """アプリメンションイベントを処理する.

        Args:
            event: Slackイベントデータ
            say: メッセージ送信用の関数
        """
        mention = event["text"]
        channel = event["channel"]
        user = event["user"]
        thread_ts = event.get("thread_ts", event.get("ts"))

        logger.info(
            f"Received mention: {mention}, channel: {channel}, user: {user}, thread: {thread_ts}"
        )

        # メンションを除去
        cleaned_mention = re.sub(r"<@[A-Z0-9]+>\s*", "", mention).strip()

        if cleaned_mention == "help":
            say(
                "わたしは、将来的なDatable Agentの試作版です。\n"
                "定型業務は設定画面から設定したワークフローを実行し、非定型業務はオンデマンドで実行します。"
            )
            return

        question = f"""
    与えられる会話履歴を参考に、以下の質問に対して、回答を日本語のMarkdown形式でお願いします.
    Markdown形式で回答しますなど、は出力せず、質問に対する回答のみを出力してください.

    質問:
    {mention}

    出力:
"""
        thread_history = None
        try:
            thread_history = app.client.conversations_replies(
                channel=channel, ts=thread_ts
            )
        except Exception as e:
            logger.error(f"Error getting thread messages: {e}")

        response = execute_langgraph(
            question=question,
            say=say,
            user=user,
            thread_ts=thread_ts,
            thread_messages=thread_history,
            app=app,
            langgraph_url=os.environ.get("LANGGRAPH_URL"),
            langgraph_token=os.environ.get("LANGGRAPH_TOKEN"),
        )

        if not response:
            say("エラーが発生しました")
