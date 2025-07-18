from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from slack_ai_agent.agents.configuration import Configuration
from slack_ai_agent.agents.prompts.deep_research_planner_query_writer_instructions import (
    report_planner_query_writer_instructions,
)
from slack_ai_agent.agents.prompts.deep_research_query_writer_instructions import (
    query_writer_instructions,
)
from slack_ai_agent.agents.prompts.deep_research_report_planner_instructions import (
    report_planner_instructions,
)
from slack_ai_agent.agents.tools.perplexity_search import perplexity_search
from slack_ai_agent.agents.tools.tavily_search import deduplicate_and_format_sources
from slack_ai_agent.agents.tools.tavily_search import tavily_search

from .models import ReportState
from .models import SearchQuery
from .models import Section
from .models import SectionState
from .utils import extract_json_from_response
from .utils import get_config_value
from .utils import parse_json_with_fallback


def generate_report_queries(state: ReportState, config: RunnableConfig) -> dict:
    """
    レポートプラン用の検索クエリ（Queries）を生成し、state全体を返す
    """
    url = state["input"].url
    url_content = state["input"]
    markdown = url_content.markdown
    title = url_content.title

    configurable = Configuration.from_runnable_config(config)
    report_structure = configurable.report_structure
    number_of_queries = configurable.number_of_queries

    if isinstance(report_structure, dict):
        report_structure = str(report_structure)

    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(
        model=writer_model_name, model_provider=writer_provider, temperature=0
    )

    # Format system instructions
    system_instructions_query = report_planner_query_writer_instructions.format(
        topic=f"Content from URL: {url} / Title: {title}",
        report_organization=f"{report_structure}\n\n重要: レポートは日本語で生成してください。",
        number_of_queries=number_of_queries,
    )

    # JSON形式で出力するようにプロンプトを設定
    system_instructions_query += """
重要: 以下のJSON形式で出力してください：

```json
{
  "queries": [
    {"search_query": "検索クエリ1"},
    {"search_query": "検索クエリ2"},
    {"search_query": "検索クエリ3"}
  ]
}
```

必ず有効なJSONを出力してください。
"""

    # JSONレスポンスを取得
    response = writer_model.invoke(
        [SystemMessage(content=system_instructions_query)]
        + [
            HumanMessage(
                content=f"Generate search queries that will help with planning the sections of the report based on the following URL content:\n\n{markdown[:5000]}..."
            )
        ]
    )

    # レスポンスをテキストとして取得
    response_text = ""
    if hasattr(response, "content"):
        response_text = str(response.content)
    else:
        response_text = str(response)

    # JSONを抽出
    json_str = extract_json_from_response(response_text)

    # JSONを解析
    results_dict = parse_json_with_fallback(json_str, {"queries": []})

    # SearchQueryオブジェクトに変換
    queries = []
    for query_dict in results_dict.get("queries", []):
        queries.append(SearchQuery(search_query=query_dict.get("search_query", "")))

    if not queries:
        # JSON解析に失敗した場合は、デフォルト値を設定
        queries = [SearchQuery(search_query="エラー: JSONの解析に失敗しました")]

    # 入力のstateをベースに、queriesフィールドだけを更新した完全なReportStateを返す
    return {
        "input": state["input"],
        "title": state["title"],
        "feedback_on_report_plan": state["feedback_on_report_plan"],
        "sections": state["sections"],
        "queries": queries,
        "completed_sections": state["completed_sections"],
        "report_sections_from_research": state["report_sections_from_research"],
        "final_report": state["final_report"],
    }


def generate_report_plan(state: ReportState, config: RunnableConfig):
    """Generate the report plan for the report."""

    url = state["input"].url
    url_content = state["input"]
    markdown = url_content.markdown
    feedback = state.get("feedback_on_report_plan", None)

    # 検索クエリ生成部分を分離
    results = generate_report_queries(state, config)

    # Web search
    query_list = [query.search_query for query in results["queries"]]  # type: ignore

    # Get the search API
    configurable = Configuration.from_runnable_config(config)
    report_structure = configurable.report_structure
    search_api = get_config_value(configurable.search_api)

    if isinstance(report_structure, dict):
        report_structure = str(report_structure)

    # Search the web - 同期バージョンを使用
    if search_api == "tavily":
        search_results = tavily_search(query=query_list)
        source_str = deduplicate_and_format_sources(
            search_results, max_tokens_per_source=1000, include_raw_content=False
        )
    elif search_api == "perplexity":
        search_results = perplexity_search(search_queries=query_list)
        source_str = deduplicate_and_format_sources(
            search_results, max_tokens_per_source=1000, include_raw_content=False
        )
    else:
        raise ValueError(f"Unsupported search API: {configurable.search_api}")

    # Format system instructions
    system_instructions_sections = report_planner_instructions.format(
        topic=f"Content from URL: {url}",
        report_organization=f"{report_structure}\n\n重要: レポートは日本語で生成してください。",
        context=f"URL Content:\n{markdown}\n\nAdditional Research:\n{source_str}",
        feedback=feedback,
    )

    # Set the planner provider
    if isinstance(configurable.planner_provider, str):
        planner_provider = configurable.planner_provider
    else:
        planner_provider = configurable.planner_provider.value  # type: ignore

    # Set the planner model
    if isinstance(configurable.planner_model, str):
        planner_model = configurable.planner_model
    else:
        planner_model = configurable.planner_model.value

    # Set the planner model
    planner_llm = init_chat_model(model=planner_model, model_provider=planner_provider)

    # JSON形式で出力するようにプロンプトを設定
    system_instructions_sections += """
重要: 以下のJSON形式で出力してください：

```json
{
  "sections": [
    {
      "headline": "セクション1のタイトル",
      "description": "セクション1の概要",
      "research": true,
      "content": ""
    },
    {
      "headline": "セクション2のタイトル",
      "description": "セクション2の概要",
      "research": false,
      "content": ""
    }
  ]
}
```

必ず有効なJSONを出力してください。
"""

    # JSONレスポンスを取得
    response = planner_llm.invoke(
        [SystemMessage(content=system_instructions_sections)]
        + [
            HumanMessage(
                content="URLコンテンツと追加調査に基づいてレポートのセクションを生成してください。レポートは日本語で作成してください。JSON形式で出力してください。"
            )
        ]
    )

    # レスポンスをテキストとして取得
    response_text = ""
    if hasattr(response, "content"):
        response_text = str(response.content)
    else:
        response_text = str(response)

    # JSONを抽出
    json_str = extract_json_from_response(response_text)

    # JSONを解析
    try:
        report_sections_dict = parse_json_with_fallback(json_str, {"sections": []})
        # Sectionsオブジェクトに変換
        sections = []
        for section_dict in report_sections_dict.get("sections", []):
            sections.append(
                Section(
                    headline=section_dict.get("headline", ""),
                    description=section_dict.get("description", ""),
                    research=section_dict.get("research", False),
                    content=section_dict.get("content", ""),
                    quotes=[],
                    references=[],
                )
            )
    except Exception:
        # JSON解析に失敗した場合は、デフォルト値を設定
        sections = [
            Section(
                headline="エラー",
                description="JSONの解析に失敗しました",
                research=False,
                content="",
                quotes=[],
                references=[],
            )
        ]

    return {"sections": sections}


def generate_queries(state: SectionState, config: RunnableConfig):
    """Generate search queries for a report section"""
    # Get state
    url = state["url"]
    url_content = state["url_content"]

    # Check if section exists in state
    if "section" not in state:
        raise KeyError(
            f"The 'section' key is missing from the state. Available keys: {list(state.keys())}. State content: {state}"
        )
    section = state["section"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    number_of_queries = configurable.number_of_queries

    # Generate queries
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(
        model=writer_model_name, model_provider=writer_provider, temperature=0
    )

    # Format system instructions
    system_instructions = query_writer_instructions.format(
        topic=f"Content from URL: {url}",
        section_topic=section.description,
        number_of_queries=number_of_queries,
    )
    system_instructions += (
        "\n\n重要: 検索クエリは日本語と英語の両方で生成してください。"
    )

    # JSON形式で出力するようにプロンプトを設定
    system_instructions += """
重要: 以下のJSON形式で出力してください：

```json
{
  "queries": [
    {"search_query": "検索クエリ1"},
    {"search_query": "検索クエリ2"},
    {"search_query": "検索クエリ3"}
  ]
}
```

必ず有効なJSONを出力してください。
"""

    # JSONレスポンスを取得
    response = writer_model.invoke(
        [SystemMessage(content=system_instructions)]
        + [
            HumanMessage(
                content=f"以下のURLコンテンツに基づいて、セクションの検索クエリを生成してください。日本語と英語の両方のクエリを含めてください：\n\n{url_content}"
            )
        ]
    )

    # レスポンスをテキストとして取得
    response_text = ""
    if hasattr(response, "content"):
        response_text = str(response.content)
    else:
        response_text = str(response)

    # JSONを抽出
    json_str = extract_json_from_response(response_text)

    # JSONを解析
    queries_dict = parse_json_with_fallback(json_str, {"queries": []})

    # SearchQueryオブジェクトに変換
    queries = []
    for query_dict in queries_dict.get("queries", []):
        queries.append(SearchQuery(search_query=query_dict.get("search_query", "")))

    if not queries:
        # JSON解析に失敗した場合は、デフォルト値を設定
        queries = [SearchQuery(search_query="エラー: JSONの解析に失敗しました")]

    return {"search_queries": queries}
