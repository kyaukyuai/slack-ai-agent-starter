"""Youtube-related tools for the LangGraph implementation."""

from typing import Optional

from langchain_community.tools import YouTubeSearchTool
from langchain_core.tools import BaseTool


def create_youtube_tool() -> Optional[BaseTool]:
    """Create youtube-related tools."""
    return YouTubeSearchTool()
