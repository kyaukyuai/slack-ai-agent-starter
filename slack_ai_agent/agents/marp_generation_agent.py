"""Marp generation agent."""

import json
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import TypedDict

from langchain.schema import HumanMessage
from langchain.schema import SystemMessage
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph

from slack_ai_agent.agents.prompts.marp_outline_prompt import OUTLINE_PROMPT
from slack_ai_agent.agents.prompts.marp_slide_content_prompts import CODE_SLIDE_PROMPT
from slack_ai_agent.agents.prompts.marp_slide_content_prompts import (
    DEFAULT_SLIDE_PROMPT,
)
from slack_ai_agent.agents.prompts.marp_slide_content_prompts import IMAGE_SLIDE_PROMPT
from slack_ai_agent.agents.prompts.marp_slide_content_prompts import QUOTE_SLIDE_PROMPT
from slack_ai_agent.agents.prompts.marp_slide_content_prompts import (
    SECTION_SLIDE_PROMPT,
)
from slack_ai_agent.agents.prompts.marp_slide_content_prompts import SPLIT_SLIDE_PROMPT
from slack_ai_agent.agents.prompts.marp_slide_content_prompts import TITLE_SLIDE_PROMPT
from slack_ai_agent.agents.tools.marp_generation import generate_marp
from slack_ai_agent.agents.tools.research import research
from slack_ai_agent.agents.utils.models import model


class MarpGenerationState(TypedDict):
    """State for Marp generation workflow."""

    requirements: str
    outline: Optional[Dict[str, Any]]
    slides: List[Dict[str, Any]]
    current_slide_index: int
    marp_path: Optional[str]


def generate_outline(state: MarpGenerationState) -> Dict[str, Any]:
    """Generate an outline for the Marp presentation.

    Args:
        state: The current state containing requirements

    Returns:
        Dict with outline
    """
    requirements = state["requirements"]

    # Format the prompt with requirements
    prompt = OUTLINE_PROMPT.format(requirements=requirements)

    # Generate the outline
    system_message = SystemMessage(content=prompt)
    human_message = HumanMessage(
        content="Generate an outline for the Marp presentation."
    )

    response = model.invoke([system_message, human_message])

    # Extract JSON from the response
    try:
        # Ensure response.content is a string
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )

        # Try to find JSON in the response
        json_start = content.find("{")
        json_end = content.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            outline = json.loads(json_str)
            return {"outline": outline, "current_slide_index": 0, "slides": []}
    except Exception as e:
        print(f"Error parsing outline JSON: {e}")

    # Fallback: create a simple outline
    return {
        "outline": {
            "title": "Presentation",
            "pages": [
                {
                    "header": "Title Slide",
                    "content": "Introduction to the topic",
                    "template": "title",
                    "policy": "Keep it simple and clear",
                }
            ],
        },
        "current_slide_index": 0,
        "slides": [],
    }


def generate_slide_content(state: MarpGenerationState) -> Dict[str, Any]:
    """Generate content for the current slide.

    Args:
        state: The current state containing outline and current slide index

    Returns:
        Dict with updated slides and current slide index
    """
    outline = state["outline"]
    current_index = state["current_slide_index"]
    slides = state["slides"]

    # Check if outline is None or if we've processed all slides
    if (
        outline is None
        or "pages" not in outline
        or current_index >= len(outline["pages"])
    ):
        return {"current_slide_index": current_index}

    # Get the current slide info from the outline
    current_slide = outline["pages"][current_index]
    template_type = current_slide.get(
        "template", "default"
    )  # Default to default if template is missing

    # Research the slide topic to get more detailed information
    slide_topic = current_slide["header"]
    try:
        research_results = research(slide_topic)
        research_summary = research_results["result"]["summary"]
    except Exception as e:
        print(f"Error researching slide topic: {e}")
        research_summary = f"Additional information about {slide_topic}"

    # Add research context to the slide info
    current_slide_with_research = current_slide.copy()
    current_slide_with_research["research_context"] = research_summary

    # Select the appropriate prompt based on template type
    if template_type == "default":
        prompt_template = DEFAULT_SLIDE_PROMPT
    elif template_type == "title":
        prompt_template = TITLE_SLIDE_PROMPT
    elif template_type == "image":
        prompt_template = IMAGE_SLIDE_PROMPT
    elif template_type == "split":
        prompt_template = SPLIT_SLIDE_PROMPT
    elif template_type == "code":
        prompt_template = CODE_SLIDE_PROMPT
    elif template_type == "quote":
        prompt_template = QUOTE_SLIDE_PROMPT
    elif template_type == "section":
        prompt_template = SECTION_SLIDE_PROMPT
    else:
        # Default to standard slide
        prompt_template = DEFAULT_SLIDE_PROMPT

    # Format the prompt with slide info including research context
    prompt = prompt_template.format(
        slide_info=json.dumps(current_slide_with_research, ensure_ascii=False)
    )

    # Generate the slide content
    system_message = SystemMessage(content=prompt)
    human_message = HumanMessage(
        content=f"Generate content for slide {current_index + 1}: {current_slide['header']}. Use the research information to create detailed and accurate content."
    )

    response = model.invoke([system_message, human_message])

    # Extract JSON from the response
    try:
        # Ensure response.content is a string
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )

        # Try to find JSON in the response
        json_start = content.find("{")
        json_end = content.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            slide_content = json.loads(json_str)
            slides.append(slide_content)
    except Exception as e:
        print(f"Error parsing slide JSON: {e}")
        # Fallback: create a simple slide
        slides.append(
            {
                "header": current_slide["header"],
                "template": template_type,
                "markdown_content": f"# {current_slide['header']}\n\n- Content placeholder",
            }
        )

    # Move to the next slide
    return {"slides": slides, "current_slide_index": current_index + 1}


def create_marp(state: MarpGenerationState) -> Dict[str, Any]:
    """Create the Marp presentation.

    Args:
        state: The current state containing slides

    Returns:
        Dict with Marp file path
    """
    outline = state["outline"]
    slides = state["slides"]

    # Check if outline is None
    if outline is None:
        title = "Presentation"
    else:
        title = outline.get("title", "Presentation")

    # Generate the Marp
    content = {"title": title, "pages": slides}
    marp_path = generate_marp(title, content)

    return {"marp_path": marp_path}


def should_continue_generating_slides(
    state: MarpGenerationState,
) -> str:
    """Determine whether to continue generating slides or create the Marp.

    Args:
        state: The current state

    Returns:
        Next node to route to
    """
    outline = state["outline"]
    current_index = state["current_slide_index"]

    # Check if outline is None or if we've processed all slides
    if (
        outline is None
        or "pages" not in outline
        or current_index >= len(outline["pages"])
    ):
        return "create_marp"
    else:
        return "generate_slide_content"


# Create the Marp generation workflow
def create_marp_generation_workflow():
    """Create the Marp generation workflow.

    Returns:
        Compiled workflow
    """
    workflow = StateGraph(MarpGenerationState)

    # Add nodes
    workflow.add_node("generate_outline", generate_outline)
    workflow.add_node("generate_slide_content", generate_slide_content)
    workflow.add_node("create_marp", create_marp)

    # Add edges
    workflow.add_edge(START, "generate_outline")
    workflow.add_edge("generate_outline", "generate_slide_content")
    workflow.add_conditional_edges(
        "generate_slide_content",
        should_continue_generating_slides,
        {
            "generate_slide_content": "generate_slide_content",
            "create_marp": "create_marp",
        },
    )
    workflow.add_edge("create_marp", END)

    return workflow.compile()


# Export the graph for langgraph_api
graph = create_marp_generation_workflow()
