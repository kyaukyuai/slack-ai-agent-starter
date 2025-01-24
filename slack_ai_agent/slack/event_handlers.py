"""Slack event handlers module.

This module provides handlers for different types of Slack events.
"""

import logging
import os
import re
from typing import Any
from typing import Dict

from dotenv import load_dotenv
from slack_bolt import App

from slack_ai_agent.slack.utils import execute_langgraph


# Set up logging
logger = logging.getLogger(__name__)

load_dotenv()


def setup_event_handlers(app: App) -> None:
    """Set up event handlers for the Slack bot.

    Args:
        app: The Slack Bolt application instance.
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

    @app.event("message")
    def handle_message_events(body: Dict[str, Any], logger: Any) -> None:
        """Handle general message events.

        Args:
            body: The message event data.
            logger: Logger instance.
        """
        logger.info(body)
