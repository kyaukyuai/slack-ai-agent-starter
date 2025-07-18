from langchain_core.runnables import RunnableConfig

from slack_ai_agent.agents.tools.tavily_search import deduplicate_and_format_sources
from slack_ai_agent.agents.tools.tavily_search import tavily_search

from .models import SectionState


def search_web(state: SectionState, config: RunnableConfig):
    """Search the web for each query, then return a list of raw sources and a formatted string of sources."""
    # Get state
    search_queries = state["search_queries"]

    # Web search
    query_list = [query.search_query for query in search_queries]

    # Search the web - 同期バージョン（perplexityでエラーが発生するためtavilyを使用）
    try:
        search_results = tavily_search(query=query_list)  # 非同期から同期に変更
        source_str = deduplicate_and_format_sources(
            search_results, max_tokens_per_source=5000, include_raw_content=True
        )
    except Exception as e:
        print(f"Error in tavily_search: {str(e)}")
        # フォールバック: 空の検索結果を返す
        source_str = "検索結果はありません。"

    return {
        "source_str": source_str,
        "search_iterations": state["search_iterations"] + 1,
    }
