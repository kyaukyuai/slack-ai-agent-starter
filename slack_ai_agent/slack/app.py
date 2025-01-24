"""Slack bot application module.

This module implements a Slack bot using the Slack Bolt framework.
It handles basic message events, interactive button clicks, and AI agent integration.
"""

import os
import sys
from pathlib import Path


# Add the project root to Python path when running this file directly
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.append(str(project_root))

from dotenv import load_dotenv
from slack_bolt import App

from slack_ai_agent.slack.handler.action_handlers import setup_action_handlers
from slack_ai_agent.slack.handler.event_handlers import setup_event_handlers
from slack_ai_agent.slack.handler.message_handlers import setup_message_handlers


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

# Set up handlers
setup_message_handlers(app)
setup_action_handlers(app)
setup_event_handlers(app)


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
