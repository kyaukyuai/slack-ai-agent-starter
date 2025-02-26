from typing import Any
from typing import Dict


def deep_research(topic: str) -> Dict[str, Any]:
    """
    Perform deep research on a given topic to create a comprehensive report.
    This tool conducts thorough research by:
    1. Planning the report structure with sections
    2. Researching each section using web search
    3. Writing detailed content for each section based on research
    4. Organizing all sections into a comprehensive final report

    Args:
        topic (str): The research topic to create a report on

    Returns:
        Dict[str, Any]: A dictionary containing:
            - report: The complete final report
            - sections: List of section titles and summaries
    """
    # Import here to avoid circular imports
    from slack_ai_agent.agents.sync_deep_research_agent import graph

    # Invoke the synchronous graph with the topic
    result = graph.invoke({"topic": topic})

    # Extract sections information
    sections_info = []
    if "sections" in result and result["sections"]:
        for section in result["sections"]:
            sections_info.append(
                {
                    "title": section.name,
                    "summary": section.description[:100] + "..."
                    if len(section.description) > 100
                    else section.description,
                }
            )

    return {
        "result": {"report": result.get("final_report", ""), "sections": sections_info}
    }
