"""Slack bot handler with AI agent integration.

This module provides the integration between the Slack bot and the AI agent,
handling message processing and response generation.
"""

import logging
from typing import Any
from typing import Dict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from slack_bolt import App

from slack_ai_agent.agents.simple_agent import create_agent
from slack_ai_agent.agents.simple_agent import run_agent


# Set up logging
logger = logging.getLogger(__name__)


load_dotenv()


def setup_bot_handlers(app: App) -> None:
    """Set up message handlers for the Slack bot with AI agent integration.

    Args:
        app: The Slack Bolt application instance.
    """
    # Create an instance of the AI agent
    try:
        agent = create_agent()
    except Exception as e:
        logger.error(f"Failed to create AI agent: {str(e)}")
        raise

    @app.message("ai")
    def handle_ai_message(message: Dict[str, Any], say: Any) -> None:
        """Handle messages that should be processed by the AI agent.

        Args:
            message: The incoming message event data.
            say: Function for sending messages to the channel.
        """
        # Extract the actual message content (removing the "ai" trigger word)
        text = message.get("text", "").lower().replace("ai", "").strip()
        if not text:
            say("Please provide a message for the AI agent to process.")
            return

        # Process the message using the AI agent
        try:
            messages = run_agent(agent, text)
            response = "No response generated."

            # Get the last message (the agent's response)
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, BaseMessage):
                    response = last_message.content

                    # Check for any tool results
                    tool_results = getattr(last_message, "additional_kwargs", {}).get(
                        "tool_results"
                    )
                    if tool_results:
                        response += f"\n\nTool Results: {tool_results}"
                else:
                    response = "Received an unexpected response format from the agent."

            say(response)

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            say(
                f"Sorry, I encountered an error while processing your message: {str(e)}"
            )
