"""Slack message handlers module."""

import logging
import os
import re
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union
from urllib.parse import urlparse

import requests  # type: ignore
from langchain_core.messages import BaseMessage
from slack_bolt import App

from slack_ai_agent.agents.simple_agent import create_agent
from slack_ai_agent.agents.simple_agent import run_agent


logger = logging.getLogger(__name__)


def download_file(url: str, token: str) -> Optional[str]:
    """Download a file from Slack and save it to .files directory.

    Args:
        url: The URL of the file to download
        token: Slack bot token for authentication

    Returns:
        Optional[str]: Path to the downloaded file, or None if download failed
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Create .files directory if it doesn't exist
        files_dir = os.path.join(os.getcwd(), ".files")
        os.makedirs(files_dir, exist_ok=True)

        # Get filename from URL and create full path
        file_name = os.path.basename(urlparse(url).path)
        file_path = os.path.join(files_dir, file_name)

        # Save file
        with open(file_path, "wb") as f:
            f.write(response.content)

        return file_path
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return None


def setup_message_handlers(app: App) -> None:
    """Set up message handlers for the Slack bot.

    Args:
        app: The Slack Bolt application instance.
    """
    # Create an instance of the AI agent
    try:
        agent = create_agent()
    except Exception as e:
        logger.error(f"Failed to create AI agent: {str(e)}")
        raise

    @app.message("hello")
    def handle_hello_message(message: Dict[str, Any], say: Any) -> None:
        """Handle incoming messages containing 'hello'.

        Args:
            message: The incoming message event data.
            say: Function for sending messages to the channel.
        """
        say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Hey there <@{message['user']}>!!!",
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Click Me"},
                        "action_id": "button_click",
                    },
                }
            ],
            text=f"Hey there <@{message['user']}>!",
        )

    @app.message(re.compile(r"^ai\s+", re.IGNORECASE))
    def handle_ai_message(message: Dict[str, Any], say: Any, client: Any) -> None:
        """Handle messages that should be processed by the AI agent.

        Args:
            message: The incoming message event data.
            say: Function for sending messages to the channel.
            client: Slack client instance.
        """
        # Extract the actual message content (removing the "ai" trigger word)
        text = message.get("text", "").lower().replace("ai", "").strip()

        # Handle file attachments
        file_paths = []
        if "files" in message and app.client.token:
            for file in message["files"]:
                if file.get("url_private"):
                    # Download the file
                    file_path = download_file(file["url_private"], app.client.token)
                    if file_path:
                        file_paths.append(file_path)

        if not text and not file_paths:
            thread_ts = message.get("thread_ts", message.get("ts"))
            say(
                text="Please provide a message or file for the AI agent to process.",
                thread_ts=thread_ts,
            )
            return

        # Process the message using the AI agent
        try:
            # Prepare the message with file paths if present
            if file_paths:
                # Format the message to include file paths for the vision tool
                text = f"{text}\nAnalyze these images: {' '.join(file_paths)}"

            messages: List[BaseMessage] = run_agent(agent, text)
            response: Union[str, List[Union[str, Dict[Any, Any]]]] = (
                "No response generated."
            )

            # Get the last message (the agent's response)
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, BaseMessage):
                    base_response = str(last_message.content)
                    tool_results = getattr(last_message, "additional_kwargs", {}).get(
                        "tool_results", ""
                    )
                    response = base_response
                    if tool_results:
                        response += f"\n\nTool Results: {tool_results}"
                else:
                    response = "Received an unexpected response format from the agent."

            # Get thread_ts from the message if it exists, otherwise use the message ts
            thread_ts = message.get("thread_ts", message.get("ts"))
            say(text=response, thread_ts=thread_ts)

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            thread_ts = message.get("thread_ts", message.get("ts"))
            say(
                text=f"Sorry, I encountered an error while processing your message: {str(e)}",
                thread_ts=thread_ts,
            )
        finally:
            # Clean up temporary files
            for file_path in file_paths:
                try:
                    os.unlink(file_path)
                except Exception as e:
                    logger.error(f"Error deleting temporary file {file_path}: {str(e)}")
