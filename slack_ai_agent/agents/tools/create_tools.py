from typing import List

from langchain.tools import Tool

from .github import create_github_tools  # type: ignore
from .memory import upsert_memory
from .python import create_python_repl_tool
from .research import research
from .slack import create_slack_tools
from .summarize import summarize
from .vision import create_vision_tool
from .youtube import create_youtube_tool


def create_tools() -> List:
    """Create and return a list of available tools.

    Returns:
        List: List of configured tools including search, memory, slack, youtube, python and research tools
    """
    tools: List = []

    # Add research tool
    tools.append(
        Tool.from_function(
            func=research,
            name="research",
            description="Useful for when you need to research a topic, gather information from multiple sources, and provide a comprehensive summary. Input should be a research topic or question.",
        )
    )

    # Add summarize tool
    tools.append(
        Tool.from_function(
            func=summarize,
            name="summarize",
            description="Useful for when you need to summarize the content of a specific URL. Input should be a URL that you want to analyze and summarize.",
        )
    )

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

    # Add GitHub tools
    if github_tools := create_github_tools():
        tools.extend(github_tools)

    # Add vision tool
    if vision_tool := create_vision_tool():
        tools.append(vision_tool)

    return tools
