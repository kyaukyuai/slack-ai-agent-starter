"""Slack utilities module.

This module provides utility functions for Slack message formatting and LangGraph integration.
"""

import logging
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
from slack_sdk.web import SlackResponse


# Set up logging
logger = logging.getLogger(__name__)

load_dotenv()

# Constants
MESSAGE_UPDATE_INTERVAL = 0.3  # seconds
BOT_MENTION_PATTERN = r"<@[A-Z0-9]+>\s*"


def format_for_slack_display(text: str) -> str:
    """Convert Markdown text for Slack display.

    Args:
        text: Text to convert

    Returns:
        str: Text converted for Slack display
    """
    # Process headings (#)
    text = re.sub(r"#+ (.+?)(?:\n|$)", r"*\1*\n", text)

    # Convert bullet points for better visibility
    text = re.sub(r"^\s*[-*]\s", "• ", text, flags=re.MULTILINE)

    # Process bold text (**text** -> *text*)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

    # Process code blocks
    text = re.sub(r"```(\w+)\n", "```\n", text)

    # Adjust line breaks between paragraphs
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Add line breaks around bullet points for better readability
    text = re.sub(r"(?<!\n)\n•", "\n\n•", text)

    return text


def extract_text_from_blocks(blocks: List[Dict[str, Any]]) -> str:
    """Extract text from Slack message blocks.

    Args:
        blocks: Slack message blocks

    Returns:
        str: Extracted text
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


def build_conversation_history(
    thread_messages: Optional[Union[Dict[str, Any], SlackResponse]] = None,
    question: str = "",
) -> List[Dict[str, str]]:
    """Build conversation history.

    Args:
        thread_messages: Thread message history
        question: Current question

    Returns:
        List[Dict[str, str]]: Constructed conversation history
    """
    messages = []
    if thread_messages and "messages" in thread_messages:
        for msg in thread_messages["messages"]:
            message_text = msg.get("text", "")

            if "blocks" in msg:
                blocks_text = extract_text_from_blocks(msg["blocks"])
                if blocks_text:
                    message_text = f"{message_text} {blocks_text}".strip()

            cleaned_text = re.sub(BOT_MENTION_PATTERN, "", message_text).strip()
            if cleaned_text:
                messages.append(
                    {
                        "role": "assistant" if msg.get("bot_id") else "user",
                        "content": cleaned_text,
                    }
                )

    if question:
        messages.append({"role": "user", "content": question})

    return messages


def update_slack_message(
    app: App,
    message: Dict[str, Any],
    user: str,
    formatted_text: str,
) -> None:
    """Update a Slack message.

    Args:
        app: Slack Bolt application instance
        message: Message to update
        user: User ID
        formatted_text: Formatted text
    """
    try:
        app.client.chat_update(
            channel=message["channel"],
            ts=message["ts"],
            text=f"<@{user}>\n{formatted_text}",
        )
    except Exception as e:
        logger.error(f"Error updating message: {e}")


def process_langgraph_stream(
    client: Any,
    thread_id: str,
    messages: List[Dict[str, str]],
    say: Any,
    user: str,
    thread_ts: Optional[str],
    app: Optional[App],
) -> Optional[str]:
    """Process LangGraph stream.

    Args:
        client: LangGraph client
        thread_id: Thread ID
        messages: Conversation history
        say: Function for sending messages
        user: User ID
        thread_ts: Thread timestamp
        app: Slack Bolt application instance

    Returns:
        Optional[str]: Generated response
    """
    final_answer = ""
    last_update = time.time()
    last_post_text = ""
    message = None
    formatted_text = ""

    for chunk in client.runs.stream(
        thread_id,
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
                        if not message:
                            message = say(
                                text=f"<@{user}>\n{formatted_text}",
                                thread_ts=thread_ts,
                            )
                        elif (
                            app
                            and (time.time() - last_update) > MESSAGE_UPDATE_INTERVAL
                        ):
                            last_update = time.time()
                            last_post_text = formatted_text
                            update_slack_message(app, message, user, formatted_text)
                    except Exception as e:
                        logger.error(f"Error updating message: {e}")

    if message and app and last_post_text != formatted_text:
        update_slack_message(app, message, user, formatted_text)

    return final_answer


def execute_langgraph(
    question: str,
    say: Any,
    user: str,
    thread_ts: Optional[str] = None,
    thread_messages: Optional[Union[Dict[str, Any], SlackResponse]] = None,
    app: Optional[App] = None,
    langgraph_url: Optional[str] = None,
    langgraph_token: Optional[str] = None,
) -> Optional[str]:
    """Execute LangGraph and generate a response.

    Args:
        question: Question text
        say: Function for sending messages
        user: User ID
        thread_ts: Thread timestamp
        thread_messages: Thread message history
        app: Slack Bolt application instance
        langgraph_url: LangGraph API URL
        langgraph_token: LangGraph API token

    Returns:
        Optional[str]: Generated response
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

        messages = build_conversation_history(thread_messages, question)
        return process_langgraph_stream(
            client, thread["thread_id"], messages, say, user, thread_ts, app
        )

    except Exception as e:
        logger.error(f"Error in execute_langgraph: {e}")
        return None
