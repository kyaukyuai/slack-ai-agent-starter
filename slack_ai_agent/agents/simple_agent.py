from typing import Any
from typing import List
from typing import Literal
from typing import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph

from slack_ai_agent.agents.utils.models import call_model
from slack_ai_agent.agents.utils.models import tool_node


# Define the config
class GraphConfig(TypedDict):
    model_name: Literal["anthropic", "openai"]


# Define the function that determines whether to continue or not
def should_continue(state: MessagesState) -> Literal["action", END]:  # type: ignore
    messages = state["messages"]
    last_message = messages[-1]
    # If the LLM makes a tool call, then we route to the "tools" node
    return "action" if last_message.tool_calls else END  # type: ignore


# Define a new graph
workflow = StateGraph(MessagesState, config_schema=GraphConfig)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)

workflow.add_edge(START, "agent")

# Set the entrypoint as `agent`
# This means that this node is the first one called
workflow.set_entry_point("agent")

# We now add a conditional edge
workflow.add_conditional_edges(
    # First, we define the start node. We use `agent`.
    # This means these are the edges taken after the `agent` node is called.
    "agent",
    # Next, we pass in the function that will determine which node is called next.
    should_continue,
)

# We now add a normal edge from `tools` to `agent`.
# This means that after `tools` is called, `agent` node is called next.
workflow.add_edge("action", "agent")

# Finally, we compile it!
# This compiles it into a LangChain Runnable,
# meaning you can use it as you would any other runnable
graph = workflow.compile()


def create_agent() -> Any:
    """Create and return an instance of the AI agent.

    Returns:
        Any: The compiled graph that serves as the AI agent.
    """
    return graph


def run_agent(agent: Any, text: str) -> List[BaseMessage]:
    """Run the AI agent with the given input text.

    Args:
        agent: The compiled graph instance.
        text: The input text to process.

    Returns:
        List[BaseMessage]: List of messages including the agent's response.
    """
    config = {"model_name": "anthropic"}  # Default to anthropic model
    result = agent.invoke(
        {"messages": [{"role": "user", "content": text}], "config": config}
    )
    return result["messages"]
