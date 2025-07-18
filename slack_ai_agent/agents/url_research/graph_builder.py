from langgraph.constants import Send
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from langgraph.types import Command
from langgraph.types import interrupt

from .content_fetcher import preprocess_url
from .models import ReportState
from .models import ReportStateInput
from .models import ReportStateOutput
from .models import Section
from .models import SectionOutputState
from .models import SectionState
from .query_generator import generate_queries
from .query_generator import generate_report_plan
from .query_generator import generate_report_queries
from .report_compiler import compile_final_report
from .search import search_web
from .section_writer import gather_completed_sections
from .section_writer import write_final_sections
from .section_writer import write_section


def go_to_build_section_with_web_research(state: ReportState, config) -> Command:
    """Go to build section with web research"""

    # Get sections
    sections = state["sections"]
    url = state["input"].url
    url_content = state["input"].markdown

    return Command(
        goto=[
            Send(
                "build_section_with_web_research",
                {
                    "url": url,
                    "url_content": url_content,
                    "section": s,
                    "search_iterations": 0,
                },
            )
            for s in sections
            if s.research
        ]
    )


def human_feedback(state: ReportState, config) -> Command:
    """Get feedback on the report plan"""

    # Get sections
    url = state["input"].url
    sections = state["sections"]
    sections_str = "\n\n".join(
        f"Section: {section.headline}\n"
        f"Description: {section.description}\n"
        f"Research needed: {'Yes' if section.research else 'No'}\n"
        for section in sections
    )

    # Get feedback on the report plan from interrupt
    feedback = interrupt(
        f"Please provide feedback on the following report plan for URL: {url}. \n\n{sections_str}\n\n Does the report plan meet your needs? Pass 'true' to approve the report plan or provide feedback to regenerate the report plan:"
    )

    # If the user approves the report plan, kick off section writing
    if isinstance(feedback, bool):
        # Treat this as approve and kick off section writing
        return Command(
            goto=[
                Send(
                    "build_section_with_web_research",
                    {
                        "url": url,
                        "url_content": state["input"].markdown,
                        "section": s,
                        "search_iterations": 0,
                    },
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
            headline="No Research Needed",
            description="No sections require research",
            research=False,
            content="",
            quotes=[],
            references=[],
        )
        return {
            "url": state.get("url", ""),
            "url_content": state.get("url_content", ""),
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
        "url": state["input"].url,
        "url_content": state["input"].markdown,
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
                "url": state["input"].url,
                "url_content": state["input"].markdown,
                "section": s,
                "report_sections_from_research": state["report_sections_from_research"],
            },
        )
        for s in state["sections"]
        if not s.research
    ]


def research_section_wrapper(state: ReportState, config):
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
            from .models import SectionState

            section_state: SectionState = {
                "url": state["input"].url,
                "url_content": state["input"].markdown,
                "section": section,
                "search_iterations": 0,
                "search_queries": [],
                "source_str": "",
                "report_sections_from_research": "",
                "completed_sections": [],
            }

            # Process the section manually instead of using a subgraph

            # Step 1: Generate queries
            queries_state = generate_queries(section_state, config)
            section_state.update(queries_state)

            # Step 2: Search web (同期化)
            search_state = search_web(section_state, config)
            section_state.update(search_state)

            # Step 3: Write section
            result = write_section(section_state, config)

            # Handle Command object with safe attribute access
            if hasattr(result, "goto") and hasattr(result, "update"):
                goto = getattr(result, "goto")
                update_dict = getattr(result, "update")

                if goto == END and isinstance(update_dict, dict):
                    if "completed_sections" in update_dict:
                        completed_sections.extend(update_dict["completed_sections"])

        except Exception as e:
            print(f"Error processing section '{section.headline}': {str(e)}")
            # Continue with next section instead of failing everything
            continue

    # Return the completed sections
    return {"completed_sections": completed_sections}


def build_graph():
    """Build the graph for the URL research agent"""

    # Section builder subgraph
    section_builder = StateGraph(SectionState, output=SectionOutputState)
    section_builder.add_node("generate_queries", generate_queries)
    section_builder.add_node("search_web", search_web)
    section_builder.add_node("write_section", write_section)

    # Add edges
    section_builder.add_edge(START, "generate_queries")
    section_builder.add_edge("generate_queries", "search_web")
    section_builder.add_edge("search_web", "write_section")

    # Main graph
    builder = StateGraph(
        ReportState,
        input=ReportStateInput,
        output=ReportStateOutput,
    )

    # 前処理ステップをグラフに追加
    builder.set_entry_point("preprocess_url")
    builder.add_node("preprocess_url", preprocess_url)
    builder.add_node("generate_report_queries", generate_report_queries)
    builder.add_node("generate_report_plan", generate_report_plan)
    builder.add_node(
        "go_to_build_section_with_web_research", go_to_build_section_with_web_research
    )
    builder.add_node("build_section_with_web_research", section_builder.compile())
    builder.add_node("gather_completed_sections", gather_completed_sections)
    builder.add_node("write_final_sections", write_final_sections)
    builder.add_node("compile_final_report", compile_final_report)

    # エッジを正しい順序で追加
    builder.add_edge("preprocess_url", "generate_report_queries")
    builder.add_edge("generate_report_queries", "generate_report_plan")
    builder.add_edge("generate_report_plan", "go_to_build_section_with_web_research")
    builder.add_edge("build_section_with_web_research", "gather_completed_sections")
    builder.add_conditional_edges(
        "gather_completed_sections",
        initiate_final_section_writing,
        ["write_final_sections"],
    )
    builder.add_edge("write_final_sections", "compile_final_report")
    builder.add_edge("compile_final_report", END)

    return builder.compile()
