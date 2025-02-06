from typing import List

from .memory import upsert_memory
from .python import create_python_repl_tool
from .search import create_search_tool
from .slack import create_slack_tools
from .youtube import create_youtube_tool


def create_tools() -> List:
    """Create and return a list of available tools.

    Returns:
        List: List of configured tools including search, memory, slack, youtube and python tools
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

    # Add youtube tool
    if youtube_tool := create_youtube_tool():
        tools.append(youtube_tool)

    # Add python REPL tool
    if python_tool := create_python_repl_tool():
        tools.append(python_tool)

    return tools
