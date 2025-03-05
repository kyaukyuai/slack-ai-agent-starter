"""PowerPoint generation agent."""

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

from slack_ai_agent.agents.prompts.powerpoint_outline_prompt import OUTLINE_PROMPT
from slack_ai_agent.agents.prompts.powerpoint_slide_content_prompts import (
    IMAGE_SLIDE_PROMPT,
)
from slack_ai_agent.agents.prompts.powerpoint_slide_content_prompts import (
    TABLE_SLIDE_PROMPT,
)
from slack_ai_agent.agents.prompts.powerpoint_slide_content_prompts import (
    TEXT_SLIDE_PROMPT,
)
from slack_ai_agent.agents.prompts.powerpoint_slide_content_prompts import (
    THREE_HORIZONTAL_FLOW_SLIDE_PROMPT,
)
from slack_ai_agent.agents.prompts.powerpoint_slide_content_prompts import (
    THREE_IMAGES_SLIDE_PROMPT,
)
from slack_ai_agent.agents.prompts.powerpoint_slide_content_prompts import (
    THREE_VERTICAL_FLOW_SLIDE_PROMPT,
)
from slack_ai_agent.agents.prompts.powerpoint_slide_content_prompts import (
    TWO_COLUMN_SLIDE_PROMPT,
)
from slack_ai_agent.agents.tools.powerpoint_generation import generate_powerpoint
from slack_ai_agent.agents.tools.research import research
from slack_ai_agent.agents.utils.models import model


class PowerPointGenerationState(TypedDict):
    """State for PowerPoint generation workflow."""

    requirements: str
    outline: Optional[Dict[str, Any]]
    slides: List[Dict[str, Any]]
    current_slide_index: int
    powerpoint_path: Optional[str]


def generate_outline(state: PowerPointGenerationState) -> Dict[str, Any]:
    """Generate an outline for the PowerPoint presentation.

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
        content="Generate an outline for the PowerPoint presentation."
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
                    "template": "text",
                    "policy": "Keep it simple and clear",
                }
            ],
        },
        "current_slide_index": 0,
        "slides": [],
    }


def generate_slide_content(state: PowerPointGenerationState) -> Dict[str, Any]:
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
        "template", "text"
    )  # Default to text if template is missing

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
    if template_type == "text":
        prompt_template = TEXT_SLIDE_PROMPT
    elif template_type == "image":
        prompt_template = IMAGE_SLIDE_PROMPT
    elif template_type == "table":
        prompt_template = TABLE_SLIDE_PROMPT
    elif template_type == "two_column":
        prompt_template = TWO_COLUMN_SLIDE_PROMPT
    elif template_type == "three_images":
        prompt_template = THREE_IMAGES_SLIDE_PROMPT
    elif template_type == "three_horizontal_flow":
        prompt_template = THREE_HORIZONTAL_FLOW_SLIDE_PROMPT
    elif template_type == "three_vertical_flow":
        prompt_template = THREE_VERTICAL_FLOW_SLIDE_PROMPT
    else:
        # Default to text slide
        prompt_template = TEXT_SLIDE_PROMPT

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
                "sections": [{"title": "Section", "content": ["Content placeholder"]}],
            }
        )

    # Move to the next slide
    return {"slides": slides, "current_slide_index": current_index + 1}


def create_powerpoint(state: PowerPointGenerationState) -> Dict[str, Any]:
    """Create the PowerPoint presentation.

    Args:
        state: The current state containing slides

    Returns:
        Dict with PowerPoint file path
    """
    outline = state["outline"]
    slides = state["slides"]

    # Check if outline is None
    if outline is None:
        title = "Presentation"
    else:
        title = outline.get("title", "Presentation")

    # Generate the PowerPoint
    content = {"title": title, "pages": slides}
    powerpoint_path = generate_powerpoint(title, content)

    return {"powerpoint_path": powerpoint_path}


def should_continue_generating_slides(
    state: PowerPointGenerationState,
) -> str:
    """Determine whether to continue generating slides or create the PowerPoint.

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
        return "create_powerpoint"
    else:
        return "generate_slide_content"


# Create the PowerPoint generation workflow
def create_powerpoint_generation_workflow():
    """Create the PowerPoint generation workflow.

    Returns:
        Compiled workflow
    """
    workflow = StateGraph(PowerPointGenerationState)

    # Add nodes
    workflow.add_node("generate_outline", generate_outline)
    workflow.add_node("generate_slide_content", generate_slide_content)
    workflow.add_node("create_powerpoint", create_powerpoint)

    # Add edges
    workflow.add_edge(START, "generate_outline")
    workflow.add_edge("generate_outline", "generate_slide_content")
    workflow.add_conditional_edges(
        "generate_slide_content",
        should_continue_generating_slides,
        {
            "generate_slide_content": "generate_slide_content",
            "create_powerpoint": "create_powerpoint",
        },
    )
    workflow.add_edge("create_powerpoint", END)

    return workflow.compile()


# Export the graph for langgraph_api
graph = create_powerpoint_generation_workflow()
