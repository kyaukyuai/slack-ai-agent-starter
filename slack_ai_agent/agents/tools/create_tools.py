from typing import List

from langchain.tools import Tool

from .deep_research import deep_research
from .github import create_github_tools  # type: ignore
from .google import create_google_tools  # type: ignore
from .memory import upsert_memory
from .python import create_python_repl_tool
from .slack import create_slack_tools
from .summarize import summarize
from .twitter import create_twitter_tools  # type: ignore
from .youtube import create_youtube_tool


def create_tools() -> List:
    """Create and return a list of available tools.

    Returns:
        List: List of configured tools including search, memory, slack, youtube, python and research tools
    """
    tools: List = []

    # Add research tool
    # tools.append(
    #     Tool.from_function(
    #         func=research,
    #         name="research",
    #         description="Useful for when you need to research a topic, gather information from multiple sources, and provide a comprehensive summary. Input should be a research topic or question.",
    #     )
    # )

    # Add deep research tool
    tools.append(
        Tool.from_function(
            func=deep_research,
            name="deep_research",
            description="Useful for when you need to perform in-depth, structured research on a complex topic. This tool creates a comprehensive report with multiple sections, performs targeted searches for each section, and compiles a detailed final report. Input should be a research topic or question that requires extensive analysis.",
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

    # Add Twitter tools
    if twitter_tools := create_twitter_tools():
        tools.extend(twitter_tools)

    # Add Google tools
    if google_tools := create_google_tools():
        tools.extend(google_tools)

    return tools
