from typing import Literal
from typing import TypedDict

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph

from slack_ai_agent.agents.utils import State
from slack_ai_agent.agents.utils import agent
from slack_ai_agent.agents.utils import load_memories_from_store
from slack_ai_agent.agents.utils import tools


# Define the config
class GraphConfig(TypedDict):
    model_name: Literal["anthropic", "openai"]


def route_tools(state: State):
    """Determine whether to use tools or end the conversation based on the last message.

    Args:
        state (schemas.State): The current state of the conversation.

    Returns:
        Literal["tools", "__end__"]: The next step in the graph.
    """
    msg = state["messages"][-1]
    print("msg: ", msg)
    if msg.tool_calls:  # type: ignore
        return "tools"

    return END


# Create the graph and add nodes
builder = StateGraph(State)
builder.add_node("load_memories", load_memories_from_store)  # type: ignore
builder.add_node("agent", agent)  # type: ignore
builder.add_node("tools", tools)  # type: ignore

# Add edges to the graph
builder.add_edge(START, "load_memories")
builder.add_edge("load_memories", "agent")
builder.add_conditional_edges("agent", route_tools, ["tools", END])
builder.add_edge("tools", "agent")

# Compile the graph
graph = builder.compile()
