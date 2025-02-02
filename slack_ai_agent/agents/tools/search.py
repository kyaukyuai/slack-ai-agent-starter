"""Search-related tools for the LangGraph implementation."""

import os
from typing import List

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import BaseTool


def create_search_tools() -> List[BaseTool]:
    """Create search-related tools."""
    tools: List[BaseTool] = []
    if os.getenv("TAVILY_API_KEY"):
        tools.append(TavilySearchResults(max_results=3))
    return tools


# Initialize search tool
search = TavilySearchResults(max_results=3)
