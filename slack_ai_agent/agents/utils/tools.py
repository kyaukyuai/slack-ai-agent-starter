import os
from typing import List

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import BaseTool


tools: List[BaseTool] = []

# Only add Tavily search if API key is available
if os.getenv("TAVILY_API_KEY"):
    tools.append(TavilySearchResults(max_results=3))
