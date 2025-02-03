"""Slack-related tools for the LangGraph implementation."""

import os
from typing import List
from typing import Optional

from langchain_community.agent_toolkits import SlackToolkit
from langchain_core.tools import BaseTool


def create_slack_tools() -> Optional[List[BaseTool]]:
    """Create Slack-related tools.

    Returns:
        Optional[List[BaseTool]]: List of Slack tools if available, None otherwise
    """
    if os.getenv("SLACK_BOT_TOKEN"):
        try:
            toolkit = SlackToolkit()
            return toolkit.get_tools()
        except Exception:
            return None
    return None
