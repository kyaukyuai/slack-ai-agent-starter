import operator
from typing import Annotated
from typing import List
from typing import Literal
from typing import TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.constants import Send  # type: ignore
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from langgraph.types import Command
from langgraph.types import interrupt
from pydantic import BaseModel
from pydantic import Field

from slack_ai_agent.agents.configuration import Configuration
from slack_ai_agent.agents.prompts.deep_research_final_section_writer_instructions import (
    final_section_writer_instructions,
)
from slack_ai_agent.agents.prompts.deep_research_planner_query_writer_instructions import (
    report_planner_query_writer_instructions,
)
from slack_ai_agent.agents.prompts.deep_research_query_writer_instructions import (
    query_writer_instructions,
)
from slack_ai_agent.agents.prompts.deep_research_report_planner_instructions import (
    report_planner_instructions,
)
from slack_ai_agent.agents.prompts.deep_research_section_grader_instructions import (
    section_grader_instructions,
)
from slack_ai_agent.agents.prompts.deep_research_section_writer_instructions import (
    section_writer_instructions,
)
from slack_ai_agent.agents.tools.perplexity_search import perplexity_search
from slack_ai_agent.agents.tools.tavily_search import deduplicate_and_format_sources
from slack_ai_agent.agents.tools.tavily_search import tavily_search_async


class SearchQuery(BaseModel):
    search_query: str = Field(..., description="Query for web search.")


class Queries(BaseModel):
    queries: List[SearchQuery] = Field(
        description="List of search queries.",
    )


class Section(BaseModel):
    name: str = Field(
        description="Name for this section of the report.",
    )
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section.",
    )
    research: bool = Field(
        description="Whether to perform web research for this section of the report."
    )
    content: str = Field(description="The content of the section.")


class Sections(BaseModel):
    sections: List[Section] = Field(
        description="Sections of the report.",
    )


class ReportState(TypedDict):
    topic: str  # Report topic
    feedback_on_report_plan: str  # Feedback on the report plan
    sections: list[Section]  # List of report sections
    completed_sections: Annotated[list, operator.add]  # Send() API key
    report_sections_from_research: (
        str  # String of any completed sections from research to write final sections
    )
    final_report: str  # Final report


class ReportStateInput(TypedDict):
    topic: str  # Report topic


class ReportStateOutput(TypedDict):
    final_report: str  # Final report


class SectionState(TypedDict):
    topic: str  # Report topic
    section: Section  # Report section
    search_iterations: int  # Number of search iterations done
    search_queries: list[SearchQuery]  # List of search queries
    source_str: str  # String of formatted source content from web search
    report_sections_from_research: (
        str  # String of any completed sections from research to write final sections
    )
    completed_sections: list[
        Section
    ]  # Final key we duplicate in outer state for Send() API


class Feedback(BaseModel):
    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
    )
    follow_up_queries: List[SearchQuery] = Field(
        description="List of follow-up search queries.",
    )


class SectionOutputState(TypedDict):
    completed_sections: list[
        Section
    ]  # Final key we duplicate in outer state for Send() API


def format_sections(sections: list[Section]) -> str:
    """Format a list of sections into a string"""
    formatted_str = ""
    for idx, section in enumerate(sections, 1):
        formatted_str += f"""
{"=" * 60}
Section {idx}: {section.name}
{"=" * 60}
Description:
{section.description}
Requires Research:
{section.research}

Content:
{section.content if section.content else "[Not yet written]"}

"""
    return formatted_str


def get_config_value(value):
    """
    Helper function to handle both string and enum cases of configuration values
    """
    return value if isinstance(value, str) else value.value


async def generate_report_plan(state: ReportState, config: RunnableConfig):
    """Generate the report plan for the report."""

    # Inputs
    topic = state["topic"]
    feedback = state.get("feedback_on_report_plan", None)

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    report_structure = configurable.report_structure
    number_of_queries = configurable.number_of_queries

    # Convert JSON object to string if necessary
    if isinstance(report_structure, dict):
        report_structure = str(report_structure)

    # Set writer model (model used for query writing and section writing)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(
        model=writer_model_name, model_provider=writer_provider, temperature=0
    )
    structured_llm = writer_model.with_structured_output(Queries)

    # Format system instructions
    system_instructions_query = report_planner_query_writer_instructions.format(
        topic=topic,
        report_organization=report_structure,
        number_of_queries=number_of_queries,
    )

    # Generate queries
    results = structured_llm.invoke(
        [SystemMessage(content=system_instructions_query)]
        + [
            HumanMessage(
                content="Generate search queries that will help with planning the sections of the report."
            )
        ]
    )

    # Web search
    query_list = [query.search_query for query in results.queries]  # type: ignore

    # Get the search API
    search_api = get_config_value(configurable.search_api)

    # Search the web
    if search_api == "tavily":
        search_results = await tavily_search_async(query_list)  # type: ignore
        source_str = deduplicate_and_format_sources(
            search_results, max_tokens_per_source=1000, include_raw_content=False
        )
    elif search_api == "perplexity":
        search_results = perplexity_search(query_list)
        source_str = deduplicate_and_format_sources(
            search_results, max_tokens_per_source=1000, include_raw_content=False
        )
    else:
        raise ValueError(f"Unsupported search API: {configurable.search_api}")

    # Format system instructions
    system_instructions_sections = report_planner_instructions.format(
        topic=topic,
        report_organization=report_structure,
        context=source_str,
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

    # Generate sections
    structured_llm = planner_llm.with_structured_output(Sections)
    report_sections = structured_llm.invoke(
        [SystemMessage(content=system_instructions_sections)]
        + [
            HumanMessage(
                content="Generate the sections of the report. Your response must include a 'sections' field containing a list of sections. Each section must have: name, description, plan, research, and content fields."
            )
        ]
    )

    # Get sections
    sections = report_sections.sections  # type: ignore

    return {"sections": sections}


def go_to_build_section_with_web_research(
    state: ReportState, config: RunnableConfig
) -> Command[Literal["build_section_with_web_research"]]:
    """Go to build section with web research"""

    # Get sections
    sections = state["sections"]
    topic = state["topic"]

    return Command(
        goto=[
            Send(
                "build_section_with_web_research",
                {"topic": topic, "section": s, "search_iterations": 0},
            )
            for s in sections
            if s.research
        ]
    )


def human_feedback(
    state: ReportState, config: RunnableConfig
) -> Command[Literal["generate_report_plan"]]:
    """Get feedback on the report plan"""

    # Get sections
    topic = state["topic"]
    sections = state["sections"]
    sections_str = "\n\n".join(
        f"Section: {section.name}\n"
        f"Description: {section.description}\n"
        f"Research needed: {'Yes' if section.research else 'No'}\n"
        for section in sections
    )

    # Get feedback on the report plan from interrupt

    feedback = interrupt(
        f"Please provide feedback on the following report plan. \n\n{sections_str}\n\n Does the report plan meet your needs? Pass 'true' to approve the report plan or provide feedback to regenerate the report plan:"
    )

    # If the user approves the report plan, kick off section writing
    # if isinstance(feedback, bool) and feedback is True:
    if isinstance(feedback, bool):
        # Treat this as approve and kick off section writing
        return Command(
            goto=[
                Send(
                    "build_section_with_web_research",
                    {"topic": topic, "section": s, "search_iterations": 0},
                )
                for s in sections
                if s.research
            ]
        )

    # If the user provides feedback, regenerate the report plan
    elif isinstance(feedback, str):
        # treat this as feedback
        return Command(
            goto="generate_report_plan", update={"feedback_on_report_plan": feedback}
        )
    else:
        raise TypeError(f"Interrupt value of type {type(feedback)} is not supported.")


def generate_queries(state: SectionState, config: RunnableConfig):
    """Generate search queries for a report section"""

    # Debugging: print state keys
    print(f"State keys in generate_queries: {list(state.keys())}")
    print(f"State content: {state}")

    # Get state
    topic = state["topic"]  # type: ignore
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
    structured_llm = writer_model.with_structured_output(Queries)

    # Format system instructions
    system_instructions = query_writer_instructions.format(
        topic=topic,
        section_topic=section.description,
        number_of_queries=number_of_queries,
    )

    # Generate queries
    queries = structured_llm.invoke(
        [SystemMessage(content=system_instructions)]
        + [HumanMessage(content="Generate search queries on the provided topic.")]
    )

    return {"search_queries": queries.queries}  # type: ignore


async def search_web(state: SectionState, config: RunnableConfig):
    """Search the web for each query, then return a list of raw sources and a formatted string of sources."""

    # Get state
    search_queries = state["search_queries"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Web search
    query_list = [query.search_query for query in search_queries]

    # Get the search API
    search_api = get_config_value(configurable.search_api)

    # Search the web
    if search_api == "tavily":
        search_results = await tavily_search_async(query_list)  # type: ignore
        source_str = deduplicate_and_format_sources(
            search_results, max_tokens_per_source=5000, include_raw_content=True
        )
    # elif search_api == "perplexity":
    #     search_results = perplexity_search(query_list)
    #     source_str = deduplicate_and_format_sources(
    #         search_results, max_tokens_per_source=5000, include_raw_content=False
    #     )
    else:
        raise ValueError(f"Unsupported search API: {configurable.search_api}")

    return {
        "source_str": source_str,
        "search_iterations": state["search_iterations"] + 1,
    }


def write_section(
    state: SectionState, config: RunnableConfig
) -> Command[Literal[END, "search_web"]]:  # type: ignore
    """Write a section of the report"""

    # Get state
    topic = state["topic"]
    section = state["section"]
    source_str = state["source_str"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Format system instructions
    system_instructions = section_writer_instructions.format(
        topic=topic,
        section_title=section.name,
        section_topic=section.description,
        context=source_str,
        section_content=section.content,
    )

    # Generate section
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(
        model=writer_model_name, model_provider=writer_provider, temperature=0
    )
    section_content = writer_model.invoke(
        [SystemMessage(content=system_instructions)]
        + [
            HumanMessage(
                content="Generate a report section based on the provided sources."
            )
        ]
    )

    # Write content to the section object
    section.content = section_content.content

    # Grade prompt
    section_grader_instructions_formatted = section_grader_instructions.format(
        topic=topic, section_topic=section.description, section=section.content
    )

    # Feedback
    structured_llm = writer_model.with_structured_output(Feedback)
    feedback = structured_llm.invoke(
        [SystemMessage(content=section_grader_instructions_formatted)]
        + [
            HumanMessage(
                content="Grade the report and consider follow-up questions for missing information:"
            )
        ]
    )

    if (
        feedback.grade == "pass"
        or state["search_iterations"] >= configurable.max_search_depth
    ):
        # Publish the section to completed sections
        return Command(update={"completed_sections": [section]}, goto=END)
    else:
        # Update the existing section with new content and update search queries
        return Command(
            update={"search_queries": feedback.follow_up_queries, "section": section},
            goto="search_web",
        )


def write_final_sections(state: SectionState, config: RunnableConfig):
    """Write final sections of the report, which do not require web search and use the completed sections as context"""

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Get state
    topic = state["topic"]
    section = state["section"]
    completed_report_sections = state["report_sections_from_research"]

    # Format system instructions
    system_instructions = final_section_writer_instructions.format(
        topic=topic,
        section_title=section.name,
        section_topic=section.description,
        context=completed_report_sections,
    )

    # Generate section
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(
        model=writer_model_name, model_provider=writer_provider, temperature=0
    )
    section_content = writer_model.invoke(
        [SystemMessage(content=system_instructions)]
        + [
            HumanMessage(
                content="Generate a report section based on the provided sources."
            )
        ]
    )

    # Write content to section
    section.content = section_content.content

    # Write the updated section to completed sections
    return {"completed_sections": [section]}


def gather_completed_sections(state: ReportState):
    """Gather completed sections from research and format them as context for writing the final sections"""

    # List of completed sections
    completed_sections = state["completed_sections"]

    # Format completed section to str to use as context for final sections
    completed_report_sections = format_sections(completed_sections)

    return {"report_sections_from_research": completed_report_sections}


def prepare_section_for_research(state: ReportState):
    """Prepare a single section for research by initializing the state for the section_builder subgraph.

    This function selects the first section that requires research and initializes the state for it.
    The section_builder subgraph will be invoked with this state.

    Returns:
        dict: Updated state with a single section initialized for research
    """
    # Find sections that require research
    research_sections = [s for s in state["sections"] if s.research]

    # If no sections require research, create a dummy section to avoid KeyError
    if not research_sections:
        dummy_section = Section(
            name="No Research Needed",
            description="No sections require research",
            research=False,
            content="",
        )
        return {
            "topic": state.get("topic", ""),
            "section": dummy_section,
            "search_iterations": 0,
            "search_queries": [],
            "source_str": "",
            "report_sections_from_research": "",
            "completed_sections": [],
        }

    # Select the first section that requires research
    section = research_sections[0]

    # Initialize the state for the section_builder subgraph
    return {
        "topic": state["topic"],
        "section": section,
        "search_iterations": 0,  # Initialize search iterations
        "search_queries": [],  # Will be populated by generate_queries
        "source_str": "",  # Will be populated by search_web
        "report_sections_from_research": "",  # Not needed for research yet
        "completed_sections": [],  # Will be populated by write_section
    }


def initiate_final_section_writing(state: ReportState) -> list[Send]:
    """Write any final sections using the Send API to parallelize the process"""

    # Kick off section writing in parallel via Send() API for any sections that do not require research
    return [
        Send(
            "write_final_sections",
            {
                "topic": state["topic"],
                "section": s,
                "report_sections_from_research": state["report_sections_from_research"],
            },
        )  # type: ignore
        for s in state["sections"]
        if not s.research
    ]


def compile_final_report(state: ReportState):
    """Compile the final report"""

    # Get sections
    sections = state["sections"]
    completed_sections = {s.name: s.content for s in state["completed_sections"]}

    # Update sections with completed content while maintaining original order
    for section in sections:
        section.content = completed_sections[section.name]

    # Compile final report
    all_sections = "\n\n".join([s.content for s in sections])

    return {"final_report": all_sections}


# Report section sub-graph --


# Define a wrapper function that ensures the section builder gets the right state
async def research_section_wrapper(state: ReportState, config: RunnableConfig):
    """
    Wrapper function that extracts proper SectionState from ReportState for the section_builder.
    This ensures the section_builder gets state with the right structure.
    """
    # Find sections that require research
    research_sections = [s for s in state["sections"] if s.research]

    # If no sections require research, return empty completed sections
    if not research_sections:
        return {"completed_sections": []}

    # Process each research section one by one
    completed_sections = []
    for section in research_sections:
        try:
            # Explicitly create a SectionState-compatible dictionary
            # Cast to SectionState to avoid type errors
            section_state: dict = {
                "topic": state["topic"],
                "section": section,
                "search_iterations": 0,
                "search_queries": [],
                "source_str": "",
                "report_sections_from_research": "",
                "completed_sections": [],
            }

            # Process the section manually instead of using a subgraph

            # Step 1: Generate queries
            queries_state = generate_queries(section_state, config)  # type: ignore
            section_state.update(queries_state)

            # Step 2: Search web (this is async)
            search_state = await search_web(section_state, config)  # type: ignore
            section_state.update(search_state)

            # Step 3: Write section
            result = write_section(section_state, config)  # type: ignore

            # Handle Command object with safe attribute access
            if hasattr(result, "goto") and hasattr(result, "update"):
                goto = getattr(result, "goto")
                update_dict = getattr(result, "update")

                if goto == END and isinstance(update_dict, dict):
                    if "completed_sections" in update_dict:
                        completed_sections.extend(update_dict["completed_sections"])

        except Exception as e:
            print(f"Error processing section '{section.name}': {str(e)}")
            # Continue with next section instead of failing everything
            continue

    # Return the completed sections
    return {"completed_sections": completed_sections}


section_builder = StateGraph(SectionState, output=SectionOutputState)
section_builder.add_node("generate_queries", generate_queries)
section_builder.add_node("search_web", search_web)
section_builder.add_node("write_section", write_section)

# Add edges
section_builder.add_edge(START, "generate_queries")
section_builder.add_edge("generate_queries", "search_web")
section_builder.add_edge("search_web", "write_section")

builder = StateGraph(
    ReportState,
    input=ReportStateInput,
    output=ReportStateOutput,
    config_schema=Configuration,
)
builder.add_node("generate_report_plan", generate_report_plan)
builder.add_node(
    "go_to_build_section_with_web_research", go_to_build_section_with_web_research
)
builder.add_node("build_section_with_web_research", section_builder.compile())
builder.add_node("gather_completed_sections", gather_completed_sections)
builder.add_node("write_final_sections", write_final_sections)
builder.add_node("compile_final_report", compile_final_report)

builder.add_edge(START, "generate_report_plan")
builder.add_edge("generate_report_plan", "go_to_build_section_with_web_research")
builder.add_edge("build_section_with_web_research", "gather_completed_sections")
builder.add_conditional_edges(
    "gather_completed_sections",
    initiate_final_section_writing,  # type: ignore
    ["write_final_sections"],
)
builder.add_edge("write_final_sections", "compile_final_report")
builder.add_edge("compile_final_report", END)

graph = builder.compile()
