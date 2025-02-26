"""Slack conversation handler module."""

import logging
import os
from typing import Any
from typing import Optional

from slack_bolt import App
from slack_sdk.web import SlackResponse

from slack_ai_agent.slack.utils import build_conversation_history
from slack_ai_agent.slack.utils import execute_langgraph


logger = logging.getLogger(__name__)

QUESTION_TEMPLATE = """
    Based on the given conversation history, please provide an answer in Markdown format.
    Please output only the answer to the question, without stating that you will respond in Markdown format.
    If the question is in English, respond in English. If the question is in Japanese, respond in Japanese.
    Do not output any timestamp or datetime information in your response.
    Keep responses clean without any date/time prefixes or suffixes.
    Do not repeat similar content.

    Conversation History:
    {thread_history}

    Question:
    {mention}

    Output:
"""


def get_thread_history(
    app: App, channel: str, thread_ts: str
) -> Optional[SlackResponse]:
    """Retrieve conversation history from a thread.

    Args:
        app: Slack application instance
        channel: Channel ID
        thread_ts: Thread timestamp

    Returns:
        Optional[SlackResponse]: Thread conversation history
    """
    try:
        return app.client.conversations_replies(channel=channel, ts=thread_ts)
    except Exception as e:
        logger.error(f"Error getting thread messages: {e}")
        return None


def handle_conversation(
    app: App,
    mention: str,
    say: Any,
    user: str,
    channel: str,
    thread_ts: str,
) -> None:
    """Process a conversation.

    Args:
        app: Slack application instance
        mention: Mention text
        say: Function for sending messages
        user: User ID
        channel: Channel ID
        thread_ts: Thread timestamp
    """
    thread_history_data = get_thread_history(app, channel, thread_ts)

    # Convert thread history to formatted string for the prompt
    history_messages = build_conversation_history(thread_history_data)
    formatted_history = ""

    # Format thread history messages into a string
    for message in history_messages:
        if message["role"] == "human" or message["role"] == "user":
            formatted_history += f"User: {message['content']}\n"
        elif message["role"] == "assistant":
            formatted_history += f"Assistant: {message['content']}\n"

    # Format the question template with both mention and thread history
    question = QUESTION_TEMPLATE.format(
        mention=mention, thread_history=formatted_history
    )

    response = execute_langgraph(
        question=question,
        say=say,
        user=user,
        thread_ts=thread_ts,
        app=app,
        langgraph_url=os.environ.get("LANGGRAPH_URL"),
        langgraph_token=os.environ.get("LANGGRAPH_TOKEN"),
    )

    if not response:
        say("An error occurred")
