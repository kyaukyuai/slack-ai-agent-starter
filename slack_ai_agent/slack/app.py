"""Slack bot application module.

This module implements a Slack bot using the Slack Bolt framework.
It handles basic message events, interactive button clicks, and AI agent integration.
"""

import os
import sys
from pathlib import Path
from typing import Any
from typing import Dict


# Add the project root to Python path when running this file directly
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.append(str(project_root))

from dotenv import load_dotenv
from slack_bolt import App

from slack_ai_agent.slack.app_mention_handler import setup_app_mention_handlers
from slack_ai_agent.slack.bot_handler import setup_bot_handlers


def init_app() -> App:
    """Initialize and configure the Slack Bolt application.

    Returns:
        App: Configured Slack Bolt application instance.
    """
    load_dotenv()

    return App(
        token=os.environ.get("SLACK_BOT_TOKEN"),
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    )


app = init_app()

# Set up AI agent integration
setup_bot_handlers(app)
setup_app_mention_handlers(app)


@app.message("hello")
def message_hello(message: Dict[str, Any], say: Any) -> None:
    """Handle incoming messages containing 'hello'.

    Args:
        message: The incoming message event data.
        say: Function for sending messages to the channel.
    """
    say(
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Hey there <@{message['user']}>!"},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Click Me"},
                    "action_id": "button_click",
                },
            }
        ],
        text=f"Hey there <@{message['user']}>!",
    )


@app.action("button_click")
def action_button_click(body: Dict[str, Any], ack: Any, say: Any) -> None:
    """Handle button click actions.

    Args:
        body: The action event data.
        ack: Function to acknowledge the action.
        say: Function for sending messages to the channel.
    """
    ack()
    say(f"<@{body['user']['id']}> clicked the button")


def start_app(port: int = 3000) -> None:
    """Start the Slack bot application.

    Args:
        port: The port number to run the application on. Defaults to 3000.
    """
    try:
        app.start(port=port)
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(
                f"Port {port} is already in use. Try setting a different port with PORT environment variable."
            )
            sys.exit(1)
        raise e


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    start_app(port=port)
