from typing import Any
from typing import Dict


def research(query: str) -> Dict[str, Any]:
    """Research a given topic using web search and summarization.

    This tool performs a comprehensive research on the given topic by:
    1. Generating appropriate search queries
    2. Gathering information from web sources
    3. Summarizing and analyzing the gathered information
    4. Providing a detailed summary with sources

    Args:
        query (str): The research topic or question to investigate

    Returns:
        Dict[str, Any]: A dictionary containing the research results with:
            - result:
                - summary: A comprehensive summary of the research
                - sources: List of sources used in the research
    """
    # Import here to avoid circular import
    from slack_ai_agent.agents.research_agent import graph

    research_result = graph.invoke({"research_topic": query})
    return {
        "result": {
            "summary": research_result["running_summary"],
            # "sources": research_result["sources_gathered"],
        }
    }
