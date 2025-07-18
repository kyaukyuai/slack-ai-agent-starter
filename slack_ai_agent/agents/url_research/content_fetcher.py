from slack_ai_agent.agents.tools.firecrawl_scrape import firecrawl_scrape

from .models import InputContent
from .models import ReportState
from .models import ReportStateInput


def fetch_url_content(url: str) -> dict:
    """
    Firecrawl APIを使ってURLから構造化コンテンツを取得する
    Returns:
        dict: {
            "title": str,
            "markdown": str,
            "metadata": dict
        }
    """
    try:
        result = firecrawl_scrape(url=url)
        markdown = result.get("markdown", "")
        metadata = result.get("metadata", {})
        title = metadata.get("title", "No title")
        return {"title": title, "markdown": markdown, "metadata": metadata}
    except Exception as e:
        print(f"Error fetching URL content: {str(e)}")
        return {
            "title": f"Error fetching content from {url}: {str(e)}",
            "markdown": "",
            "metadata": {},
        }


def preprocess_url(state: ReportStateInput) -> ReportState:
    """
    URLからコンテンツを取得し、初期状態を設定する
    """
    url = state["url"]
    url_content = fetch_url_content(url)

    return {
        "input": InputContent(
            url=url,
            title=url_content["title"],
            markdown=url_content["markdown"],
            metadata=url_content["metadata"],
        ),
        "title": "",
        "feedback_on_report_plan": "",
        "sections": [],
        "queries": [],
        "completed_sections": [],
        "report_sections_from_research": "",
        "final_report": "",
    }
