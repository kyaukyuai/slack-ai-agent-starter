from dataclasses import dataclass
from dataclasses import field
from typing import Optional

from langchain.schema import HumanMessage
from langchain.schema import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph

from slack_ai_agent.agents.prompts.summarizer_instructions import (
    SUMMARIZER_INSTRUCTIONS,
)
from slack_ai_agent.agents.tools.firecrawl_scrape import firecrawl_scrape
from slack_ai_agent.agents.utils.models import model


@dataclass(kw_only=True)
class SummarizeState:
    scrape_result: Optional[str] = field(default=None)
    summarize_url: Optional[str] = field(default=None)
    summarize_result: Optional[str] = field(default=None)
    summarize_loop_count: int = field(default=0)


@dataclass(kw_only=True)
class SummarizeStateInput:
    summarize_url: Optional[str] = field(default=None)


@dataclass(kw_only=True)
class SummarizeStateOutput:
    summarize_result: Optional[str] = field(default=None)


def scrape_url(state: SummarizeState, config: RunnableConfig):
    """Scrape the URL.

    Args:
        state: The current state containing the URL to scrape
        config: The runnable configuration

    Returns:
        dict: Dictionary containing the scraped result
    """
    scrape_result = firecrawl_scrape(url=state.summarize_url)

    return {
        "scrape_result": scrape_result,
    }


def summarize_sources(state: SummarizeState, config: RunnableConfig):
    """Summarize the gathered sources"""

    # Existing summary
    existing_summary = state.summarize_result

    # Most recent web research
    most_recent_web_research = state.scrape_result

    # Build the human message
    if existing_summary:
        human_message_content = (
            f"<User Input> \n {state.summarize_url} \n <User Input>\n\n"
            f"<Existing Summary> \n {existing_summary} \n <Existing Summary>\n\n"
            f"<New Search Results> \n {most_recent_web_research} \n <New Search Results>"
        )
    else:
        human_message_content = (
            f"<User Input> \n {state.summarize_url} \n <User Input>\n\n"
            f"<Search Results> \n {most_recent_web_research} \n <Search Results>"
        )

    # Run the LLM
    result = model.invoke(
        [
            SystemMessage(content=SUMMARIZER_INSTRUCTIONS),
            HumanMessage(content=human_message_content),
        ]
    )

    summarize_result = result.content

    return {"summarize_result": summarize_result}


builder = StateGraph(
    SummarizeState, input=SummarizeStateInput, output=SummarizeStateOutput
)
builder.add_node("scrape_url", scrape_url)
builder.add_node("summarize_sources", summarize_sources)

builder.add_edge(START, "scrape_url")
builder.add_edge("scrape_url", "summarize_sources")
builder.add_edge("summarize_sources", END)

graph = builder.compile()
