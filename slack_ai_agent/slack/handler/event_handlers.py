"""Slack event handlers module.

This module provides handlers for different types of Slack events.
"""

import logging
import re
from typing import Any
from typing import Dict

from dotenv import load_dotenv
from slack_bolt import App

from slack_ai_agent.slack.handler.conversation import handle_conversation


# Set up logging
logger = logging.getLogger(__name__)

load_dotenv()

HELP_MESSAGE = (
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
        """Handle app mention events.

        Args:
            event: Slack event data
            say: Function for sending messages
        """
        # スレッド内のメッセージは message イベントで処理するためスキップ
        if event.get("thread_ts"):
            return

        mention = event["text"]
        channel = event["channel"]
        user = event["user"]
        thread_ts = event["ts"]  # 新しいスレッドを作成（ts は必ず存在する）

        logger.info(
            f"Received mention: {mention}, channel: {channel}, user: {user}, thread: {thread_ts}"
        )

        cleaned_mention = re.sub(r"<@[A-Z0-9]+>\s*", "", mention).strip()

        if cleaned_mention == "help":
            say(HELP_MESSAGE)
            return

        handle_conversation(app, mention, say, user, channel, thread_ts)

    @app.event("message")
    def handle_message_events(
        body: Dict[str, Any],
        logger: Any,
        say: Any = None,
    ) -> None:
        """Handle general message events.

        Args:
            body: The message event data.
            logger: Logger instance.
        """
        logger.info(body)

        # Only process messages in threads
        event = body.get("event", {})
        if event.get("type") != "message" or not event.get("thread_ts"):
            return

        # Skip if it has subtype
        if event.get("subtype"):
            return

        channel = event.get("channel")
        thread_ts = event.get("thread_ts")

        if not channel or not thread_ts:
            return

        try:
            # Get all messages in the thread
            result = app.client.conversations_replies(channel=channel, ts=thread_ts)
            if not result or not result.get("messages"):
                return

            # Get bot ID
            bot_id = app.client.auth_test()["user_id"]
            text = event.get("text", "")
            user = event.get("user")

            if not text or not user:
                logger.error("Message text or user ID is missing")
                return

            # Skip if the message starts with "ai"
            if re.match(r"^ai\s+", text, re.IGNORECASE):
                return

            # Skip if it's a bot message that's not in a thread
            if event.get("bot_id") and not event.get("thread_ts"):
                return

            # Check if this is a thread started by the bot
            parent_message = result["messages"][0]
            is_bot_thread = parent_message.get("bot_id") is not None

            # Check if bot was mentioned in any previous message in the thread
            bot_mentioned = False
            for message in result["messages"]:
                if f"<@{bot_id}>" in message.get("text", ""):
                    bot_mentioned = True
                    break

            # Process if any of:
            # 1. The message mentions the bot directly
            # 2. The thread was started by the bot
            # 3. The bot was mentioned in any previous message in the thread
            if f"<@{bot_id}>" in text or is_bot_thread or bot_mentioned:
                if say:  # Only process if say function is available
                    handle_conversation(app, text, say, user, channel, thread_ts)

        except Exception as e:
            logger.error(f"Error processing thread message: {str(e)}")
