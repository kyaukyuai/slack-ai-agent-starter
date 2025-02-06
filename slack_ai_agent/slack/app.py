"""Slack bot application module.
This module implements a Slack bot using the Slack Bolt framework.
It handles basic message events, interactive button clicks, and AI agent integration.
"""

import logging
import os
import sys
from logging import getLogger
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from slack_bolt import App

from slack_ai_agent.slack.handler import setup_action_handlers
from slack_ai_agent.slack.handler import setup_event_handlers
from slack_ai_agent.slack.handler import setup_message_handlers


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("slack_bot.log")],
)

logger = getLogger(__name__)


class SlackBotApp:
    """SlackBot application class that handles initialization and startup."""

    DEFAULT_PORT = 3000

    def __init__(self):
        self._setup_project_path()
        self.app = self._initialize_app()
        self._setup_handlers()

    @staticmethod
    def _setup_project_path() -> None:
        """Add project root to Python path when running directly."""
        if __name__ == "__main__":
            project_root = Path(__file__).parent.parent.parent
            sys.path.append(str(project_root))

    def _initialize_app(self) -> App:
        """Initialize and configure the Slack Bolt application.

        Returns:
            App: Configured Slack Bolt application instance.

        Raises:
            ValueError: If required environment variables are not set.
        """
        load_dotenv()

        bot_token = os.environ.get("SLACK_BOT_TOKEN")
        signing_secret = os.environ.get("SLACK_SIGNING_SECRET")

        if not bot_token or not signing_secret:
            raise ValueError(
                "Missing required environment variables: "
                "SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET must be set"
            )

        return App(token=bot_token, signing_secret=signing_secret)

    def _setup_handlers(self) -> None:
        """Set up all message, action, and event handlers."""
        setup_message_handlers(self.app)
        setup_action_handlers(self.app)
        setup_event_handlers(self.app)

    def start(self, port: Optional[int] = None) -> None:
        """Start the Slack bot application.

        Args:
            port: The port number to run the application on.
                 Defaults to DEFAULT_PORT if not specified.

        Raises:
            SystemExit: If the specified port is already in use.
        """
        try:
            port = port or self.DEFAULT_PORT
            logger.info(f"Starting Slack bot application on port {port}")
            self.app.start(port=port)

        except OSError as e:
            if e.errno == 48:  # Address already in use
                logger.error(f"Port {port} is already in use")
                raise SystemExit(
                    f"Port {port} is already in use. "
                    "Try setting a different port with PORT environment variable."
                )
            raise


def is_development_mode() -> bool:
    """Check if the application is running in development mode."""
    return os.environ.get("ENVIRONMENT", "development").lower() == "development"


def main() -> None:
    """Main entry point for the application with auto-reloading support."""
    if is_development_mode() and os.environ.get("HUPPER_RELOAD") is None:
        import hupper  # type: ignore[import-untyped]

        hupper.start_reloader("slack_ai_agent.slack.app.main")

    port = int(os.environ.get("PORT", SlackBotApp.DEFAULT_PORT))
    slack_bot = SlackBotApp()
    slack_bot.start(port=port)


if __name__ == "__main__":
    main()
