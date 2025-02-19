from typing import Any
from typing import Dict


def summarize(url: str) -> Dict[str, Any]:
    """Summarize the content of a given URL.

    This tool performs a comprehensive summarization by:
    1. Scraping the content from the provided URL
    2. Analyzing and summarizing the gathered information
    3. Providing a detailed summary of the content

    Args:
        url (str): The URL to summarize

    Returns:
        Dict[str, Any]: A dictionary containing the summarization results with:
            - result:
                - summary: A comprehensive summary of the URL content
    """
    # Import here to avoid circular import
    from slack_ai_agent.agents.summarize_agent import graph

    summarize_result = graph.invoke({"summarize_url": url})
    return {
        "result": {
            "summary": summarize_result["summarize_result"],
        }
    }
