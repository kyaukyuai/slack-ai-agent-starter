from typing import Literal
from typing import TypedDict

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from slack_ai_agent.agents.base import agent
from slack_ai_agent.agents.store import load_memories
from slack_ai_agent.agents.tools import search
from slack_ai_agent.agents.tools import upsert_memory
from slack_ai_agent.agents.types import State


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
builder.add_node("load_memories", load_memories)  # type: ignore
builder.add_node("agent", agent)  # type: ignore
builder.add_node("tools", ToolNode([upsert_memory, search]))

# Add edges to the graph
builder.add_edge(START, "load_memories")
builder.add_edge("load_memories", "agent")
builder.add_conditional_edges("agent", route_tools, ["tools", END])
builder.add_edge("tools", "agent")

# Compile the graph
graph = builder.compile()
