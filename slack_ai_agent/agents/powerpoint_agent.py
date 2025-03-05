"""PowerPoint agent."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph

from slack_ai_agent.agents.powerpoint_generation_agent import (
    create_powerpoint_generation_workflow,
)
from slack_ai_agent.agents.powerpoint_requirements_agent import (
    create_requirements_definition_workflow,
)


class PowerPointAgentState(TypedDict):
    """State for PowerPoint agent workflow."""

    messages: List[Dict[str, Any]]
    requirements: str
    powerpoint_path: Optional[str]


def create_powerpoint_agent():
    """Create the PowerPoint agent workflow.

    Returns:
        Compiled workflow
    """
    # Create the requirements definition workflow
    requirements_workflow = create_requirements_definition_workflow()

    # Create the PowerPoint generation workflow
    generation_workflow = create_powerpoint_generation_workflow()

    # Create the main workflow
    workflow = StateGraph(PowerPointAgentState)

    # Add nodes
    workflow.add_node("define_requirements", requirements_workflow)
    workflow.add_node("generate_powerpoint", generation_workflow)

    # Add edges
    workflow.add_edge(START, "define_requirements")

    # Connect requirements workflow to generation workflow
    def prepare_for_generation(state: PowerPointAgentState) -> Dict[str, Any]:
        """Prepare the state for PowerPoint generation.

        Args:
            state: The current state

        Returns:
            Dict with requirements
        """
        return {"requirements": state["requirements"]}

    # Use a different approach for edge transformation
    workflow.set_entry_point("define_requirements")
    workflow.add_edge("define_requirements", "generate_powerpoint")

    # Add a node for transformation
    workflow.add_node("prepare_for_generation", prepare_for_generation)
    workflow.add_edge("define_requirements", "prepare_for_generation")
    workflow.add_edge("prepare_for_generation", "generate_powerpoint")

    # Connect generation workflow to end
    def finalize_result(state: PowerPointAgentState) -> Dict[str, Any]:
        """Finalize the result.

        Args:
            state: The current state

        Returns:
            Dict with PowerPoint path
        """
        return {"powerpoint_path": state["powerpoint_path"]}

    # Add a node for final transformation
    workflow.add_node("finalize_result", finalize_result)
    workflow.add_edge("generate_powerpoint", "finalize_result")
    workflow.add_edge("finalize_result", END)

    return workflow.compile()


def run_powerpoint_agent(
    messages: List[Dict[str, Any]], config: Optional[RunnableConfig] = None
):
    """Run the PowerPoint agent.

    Args:
        messages: List of messages
        config: Optional runnable config

    Returns:
        Dict with PowerPoint path
    """
    agent = create_powerpoint_agent()

    # Initialize state
    state = {"messages": messages, "requirements": "", "powerpoint_path": None}

    # Run the agent
    result = agent.invoke(state, config=config)

    return result


# Export the graph for langgraph_api
graph = create_powerpoint_agent()
