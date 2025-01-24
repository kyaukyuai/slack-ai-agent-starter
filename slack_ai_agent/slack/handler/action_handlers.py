"""Slack action handlers module.

This module provides handlers for different types of Slack actions.
"""

import logging
from typing import Any
from typing import Dict

from slack_bolt import App


# Set up logging
logger = logging.getLogger(__name__)


def setup_action_handlers(app: App) -> None:
    """Set up action handlers for the Slack bot.

    Args:
        app: The Slack Bolt application instance.
    """

    @app.action("button_click")
    def handle_button_click(body: Dict[str, Any], ack: Any, say: Any) -> None:
        """Handle button click actions.

        Args:
            body: The action event data.
            ack: Function to acknowledge the action.
            say: Function for sending messages to the channel.
        """
        ack()
        say(f"<@{body['user']['id']}> clicked the button")
