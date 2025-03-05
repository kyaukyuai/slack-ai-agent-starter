"""PowerPoint requirements agent."""

from typing import Any
from typing import Dict
from typing import TypedDict

from langchain.schema import HumanMessage
from langchain.schema import SystemMessage
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from pydantic import BaseModel
from pydantic import Field

from slack_ai_agent.agents.prompts.powerpoint_requirements_prompt import (
    REQUIREMENTS_PROMPT,
)
from slack_ai_agent.agents.sync_deep_research_agent import graph as research_graph
from slack_ai_agent.agents.utils.models import model


class Judgement(BaseModel):
    """Judgement model for checking if requirements are complete."""

    judge: bool = Field(default=False, description="判定結果")
    reason: str = Field(default="", description="判定理由")


class RequirementsState(TypedDict):
    """State for requirements definition workflow."""

    message: str
    judgement_result: bool
    judgement_reason: str
    requirements: str
    research_result: str
    assistant_response: str


class RequirementsStateInput(TypedDict):
    """Input state for requirements definition workflow."""

    message: str


class RequirementsStateOutput(TypedDict):
    """Output state for requirements definition workflow."""

    requirements: str


def research_topic(state: RequirementsState) -> Dict[str, Any]:
    """Research the topic using sync_deep_research_agent.

    Args:
        state: The current state containing the message

    Returns:
        Dict with research result
    """
    # Get the message
    topic = state["message"]

    # Use sync_deep_research_agent to research the topic
    research_result = research_graph.invoke({"topic": topic})

    # Get the final report from the research result
    final_report = research_result.get("final_report", "")

    return {"research_result": final_report}


def answering_node(state: RequirementsState) -> Dict[str, Any]:
    """Generate a response based on the user's input and research result.

    Args:
        state: The current state containing the message and research result

    Returns:
        Dict with assistant's response
    """
    # Get the message and research result
    message = state["message"]
    research_result = state["research_result"]

    # Use the requirements prompt with research result
    prompt = REQUIREMENTS_PROMPT + "\n\n# 調査結果\n" + research_result
    system_message = SystemMessage(content=prompt)
    human_message = HumanMessage(content=message)

    answer = model.invoke([system_message, human_message])

    return {"assistant_response": answer.content}


def check_node(state: RequirementsState) -> Dict[str, Any]:
    """Check if the user has approved the requirements.

    Args:
        state: The current state containing the assistant's response

    Returns:
        Dict with judgement result and reason
    """
    # For simplicity, we'll assume the requirements are approved
    # In a real implementation, you would check with the user

    # Use the assistant's response as the requirements
    assistant_response = state["assistant_response"]

    return {
        "judgement_result": True,
        "judgement_reason": "自動承認",
        "requirements": assistant_response,
    }


# Create the requirements definition workflow
def create_requirements_definition_workflow():
    """Create the requirements definition workflow.

    Returns:
        Compiled workflow
    """
    workflow = StateGraph(
        RequirementsState, input=RequirementsStateInput, output=RequirementsStateOutput
    )

    # Add nodes
    workflow.add_node("research", research_topic)
    workflow.add_node("answering", answering_node)
    workflow.add_node("check", check_node)

    # Add edges
    workflow.add_edge(START, "research")
    workflow.add_edge("research", "answering")
    workflow.add_edge("answering", "check")
    workflow.add_edge("check", END)  # Always end after check since we auto-approve

    return workflow.compile()


# Export the graph for langgraph_api
graph = create_requirements_definition_workflow()
