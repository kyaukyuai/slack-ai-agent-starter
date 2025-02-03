from typing import List

from .memory import upsert_memory
from .search import create_search_tool
from .slack import create_slack_tools


def create_tools() -> List:
    """Create and return a list of available tools.

    Returns:
        List: List of configured tools including search and memory tools
    """
    tools: List = []

    # Add search tool if available
    if search_tool := create_search_tool():
        tools.append(search_tool)

    # Add memory tool
    tools.append(upsert_memory)

    # Add slack tool
    if slack_tools := create_slack_tools():
        tools.extend(slack_tools)

    return tools
