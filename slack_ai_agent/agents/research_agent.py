import json
import operator
from dataclasses import dataclass
from dataclasses import field
from typing import Annotated
from typing import Literal
from typing import Optional

from langchain.schema import HumanMessage
from langchain.schema import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph

from slack_ai_agent.agents.prompts.query_writer_instructions import (
    QUERY_WRITER_INSTRUCTIONS,
)
from slack_ai_agent.agents.prompts.reflaction_instructions import (
    REFLECTION_INSTRUCTIONS,
)
from slack_ai_agent.agents.prompts.summarizer_instructions import (
    SUMMARIZER_INSTRUCTIONS,
)
from slack_ai_agent.agents.tools.tavily_search import deduplicate_and_format_sources
from slack_ai_agent.agents.tools.tavily_search import format_sources
from slack_ai_agent.agents.tools.tavily_search import tavily_search
from slack_ai_agent.agents.utils.models import model


@dataclass(kw_only=True)
class SummaryState:
    research_topic: Optional[str] = field(default=None)  # Report topic
    search_query: Optional[str] = field(default=None)  # Search query
    web_research_results: Annotated[list, operator.add] = field(default_factory=list)
    sources_gathered: Annotated[list, operator.add] = field(default_factory=list)
    research_loop_count: int = field(default=0)  # Research loop count
    running_summary: Optional[str] = field(default=None)  # Final report


@dataclass(kw_only=True)
class SummaryStateInput:
    research_topic: Optional[str] = field(default=None)  # Report topic


@dataclass(kw_only=True)
class SummaryStateOutput:
    running_summary: Optional[str] = field(default=None)  # Final report


def generate_query(state: SummaryState, config: RunnableConfig):
    """Generate a query for web search"""

    # Format the prompt
    query_writer_instructions_formatted = QUERY_WRITER_INSTRUCTIONS.format(
        research_topic=state.research_topic
    )

    result = model.invoke(
        [
            SystemMessage(content=query_writer_instructions_formatted),
            HumanMessage(content="Generate a query for web search:"),
        ]
    )

    if isinstance(result.content, str):
        try:
            # Try to parse the entire content as JSON
            query = json.loads(result.content)
            if "query" in query:
                return {"search_query": query["query"]}

            # If no query key, look for JSON-like structure in the text
            json_start = result.content.find("{")
            json_end = result.content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = result.content[json_start:json_end]
                try:
                    query = json.loads(json_str)
                    if "query" in query:
                        return {"search_query": query["query"]}
                except json.JSONDecodeError:
                    pass  # Continue to fallback
        except json.JSONDecodeError as e:
            print(f"JSON parsing error in generate_query: {e}")
            print(f"Content was: {result.content}")
        except Exception as e:
            print(f"Unexpected error in generate_query: {e}")
            print(f"Content was: {result.content}")

    # Fallback: use the research topic as the query
    print(f"Using fallback query for topic: {state.research_topic}")
    return {"search_query": state.research_topic}


def web_research(state: SummaryState, config: RunnableConfig):
    """Gather information from the web"""

    search_results = tavily_search(
        query=state.search_query, include_raw_content=True, max_results=1
    )
    search_str = deduplicate_and_format_sources(
        search_results, max_tokens_per_source=1000, include_raw_content=True
    )

    return {
        "sources_gathered": [format_sources(search_results)],
        "research_loop_count": state.research_loop_count + 1,
        "web_research_results": [search_str],
    }


def summarize_sources(state: SummaryState, config: RunnableConfig):
    """Summarize the gathered sources"""

    # Existing summary
    existing_summary = state.running_summary

    # Most recent web research
    most_recent_web_research = state.web_research_results[-1]

    # Build the human message
    if existing_summary:
        human_message_content = (
            f"<User Input> \n {state.research_topic} \n <User Input>\n\n"
            f"<Existing Summary> \n {existing_summary} \n <Existing Summary>\n\n"
            f"<New Search Results> \n {most_recent_web_research} \n <New Search Results>"
        )
    else:
        human_message_content = (
            f"<User Input> \n {state.research_topic} \n <User Input>\n\n"
            f"<Search Results> \n {most_recent_web_research} \n <Search Results>"
        )

    # Run the LLM
    result = model.invoke(
        [
            SystemMessage(content=SUMMARIZER_INSTRUCTIONS),
            HumanMessage(content=human_message_content),
        ]
    )

    running_summary = result.content

    return {"running_summary": running_summary}


def reflect_on_summary(state: SummaryState, config: RunnableConfig):
    """Reflect on the summary and generate a follow-up query"""
    result = model.invoke(
        [
            SystemMessage(
                content=REFLECTION_INSTRUCTIONS.format(
                    research_topic=state.research_topic
                )
            ),
            HumanMessage(
                content=f"Identify a knowledge gap and generate a follow-up web search query based on our existing knowledge: {state.running_summary}"
            ),
        ]
    )

    if not isinstance(result.content, str):
        print("LLM returned non-string content in reflect_on_summary")
        return {"search_query": f"Tell me more about {state.research_topic}"}

    try:
        # First try to parse the entire content as JSON
        try:
            follow_up_query = json.loads(result.content)
            query = follow_up_query.get("follow_up_query")
            if query:
                return {"search_query": query}
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the content
            json_start = result.content.find("{")
            json_end = result.content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = result.content[json_start:json_end]
                try:
                    follow_up_query = json.loads(json_str)
                    query = follow_up_query.get("follow_up_query")
                    if query:
                        return {"search_query": query}
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error in extracted content: {e}")
                    print(f"Extracted content was: {json_str}")
    except Exception as e:
        print(f"Unexpected error in reflect_on_summary: {e}")
        print(f"Content was: {result.content}")

    # Fallback to a placeholder query
    print(f"Using fallback query for topic: {state.research_topic}")
    return {"search_query": f"Tell me more about {state.research_topic}"}


def finalize_summary(state: SummaryState):
    """Finalize the summary"""

    # Format all accumulated sources into a single bulleted list
    all_sources = "\n".join(source for source in state.sources_gathered)
    state.running_summary = (
        f"## Summary\n\n{state.running_summary}\n\n ### Sources:\n{all_sources}"
    )
    return {"running_summary": state.running_summary}


def route_research(
    state: SummaryState, config: RunnableConfig
) -> Literal["finalize_summary", "web_research"]:
    """Route the research based on the follow-up query"""

    if state.research_loop_count <= 3:
        return "web_research"
    else:
        return "finalize_summary"


builder = StateGraph(SummaryState, input=SummaryStateInput, output=SummaryStateOutput)
builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("summarize_sources", summarize_sources)
builder.add_node("reflect_on_summary", reflect_on_summary)
builder.add_node("finalize_summary", finalize_summary)

builder.add_edge(START, "generate_query")
builder.add_edge("generate_query", "web_research")
builder.add_edge("web_research", "summarize_sources")
builder.add_edge("summarize_sources", "reflect_on_summary")
builder.add_conditional_edges("reflect_on_summary", route_research)
builder.add_edge("finalize_summary", END)

graph = builder.compile()
