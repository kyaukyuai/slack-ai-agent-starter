"""Search-related tools for the LangGraph implementation."""

import os
from typing import Optional

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import BaseTool


def create_search_tool() -> Optional[BaseTool]:
    """Create search-related tools."""
    if os.getenv("TAVILY_API_KEY"):
        return TavilySearchResults(max_results=3)
    return None
