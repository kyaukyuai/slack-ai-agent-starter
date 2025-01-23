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

    @app.event("app_home_opened")
    def update_home_tab(client: Any, event: Dict[str, Any], logger: Any) -> None:
        """Update the app home tab when a user opens it.

        Args:
            client: The Slack client instance
            event: The event data
            logger: Logger instance
        """
        try:
            client.views_publish(
                user_id=event["user"],
                view={
                    "type": "home",
                    "callback_id": "home_view",
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": "Welcome to AI Assistant! :wave:",
                                "emoji": True,
                            },
                        },
                        {"type": "divider"},
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*About this AI Assistant*\n\nProvides contextually appropriate responses through advanced natural language processing that considers conversation history. Also supports improving work efficiency through automation of routine tasks and support for non-routine tasks.",
                            },
                        },
                        {"type": "divider"},
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*Main Features*\n\n:speech_balloon: *Conversation Features*\n• Ask questions by mentioning (e.g., @AI Assistant hello)\n• Responses that consider thread conversation history\n• Task execution through natural dialogue\n\n:gear: *Work Automation*\n• Automatic execution of routine tasks\n• Customizable workflows\n• Assistance with non-routine tasks",
                            },
                        },
                        {"type": "divider"},
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*Available Commands*\n\n• `help` - Basic usage explanation\n• `ai [question]` - Direct questions to AI\n• `hello` - Greeting and simple conversation",
                            },
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*Best Practices*\n\n1. Be specific with questions: For more accurate answers\n2. Use threads: Maintain context by grouping related conversations\n3. Feedback: Add details as needed for better responses",
                            },
                        },
                        {"type": "divider"},
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": "Try the `help` command for detailed usage instructions :sparkles: Feel free to mention me if you need support",
                                }
                            ],
                        },
                    ],
                },
            )
        except Exception as e:
            logger.error(f"Error updating home tab: {e}")

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
                "*Main Features of AI Assistant* :robot_face:\n\n"
                "*1. Conversation Features*\n"
                "• Question answering via mentions (e.g. @AI Assistant hello)\n"
                "• Response generation considering thread conversation history\n"
                "• Task execution through natural dialogue\n\n"
                "*2. Commands*\n"
                "• `hello` - Display greeting and conversation button\n"
                "• `ai [question]` - Direct questions to AI agent\n"
                "• `help` - Display this help message\n\n"
                "*3. Features*\n"
                "• Context-aware responses using advanced natural language processing\n"
                "• Thread-based conversation history management\n"
                "• Interactive operations via buttons\n"
                "• Appropriate feedback on error occurrence\n\n"
                "Please check the App Home for detailed usage instructions :house:"
            )
            return

        question = f"""
    Based on the given conversation history, please provide an answer to the following question in Markdown format.
    Please output only the answer to the question, without stating that you will respond in Markdown format.

    Question:
    {mention}

    Output:
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
