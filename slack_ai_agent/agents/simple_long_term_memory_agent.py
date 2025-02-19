from typing import Any
from typing import List
from typing import Literal
from typing import TypedDict

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from slack_ai_agent.agents.tools import create_tools
from slack_ai_agent.agents.utils import State
from slack_ai_agent.agents.utils import agent
from slack_ai_agent.agents.utils import load_memories


# Define the config
class GraphConfig(TypedDict):
    model_name: Literal["anthropic", "openai"]


def get_tool_calls(msg: Any) -> List[dict]:
    """Extract all tool calls from a message.

    Args:
        msg: The message to extract tool calls from.

    Returns:
        List[dict]: List of tool calls.
    """
    tool_calls = []

    # Check content for tool_use type items
    if isinstance(msg.content, list):
        for item in msg.content:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                tool_calls.append(item)

    # Check additional_kwargs for tool_calls
    if hasattr(msg, "additional_kwargs"):
        calls = msg.additional_kwargs.get("tool_calls", [])
        if isinstance(calls, list):
            tool_calls.extend(calls)

    return tool_calls


def route_tools(state: State):
    """Determine whether to use tools or end the conversation based on the last message.

    Args:
        state (schemas.State): The current state of the conversation.

    Returns:
        Literal["tools", "__end__"]: The next step in the graph.
    """
    msg = state["messages"][-1]
    print("msg: ", msg)

    # Get all tool calls first
    tool_calls = get_tool_calls(msg)
    if tool_calls:
        print("Routing to tools")
        return "tools"

    print("Routing to END")
    return END


# Create the graph and add nodes
builder = StateGraph(State)
builder.add_node("load_memories", load_memories)  # type: ignore
builder.add_node("agent", agent)  # type: ignore
builder.add_node("tools", ToolNode(tools=create_tools()))  # type: ignore

# Add edges to the graph
builder.add_edge(START, "load_memories")
builder.add_edge("load_memories", "agent")
builder.add_conditional_edges("agent", route_tools, ["tools", END])
builder.add_edge("tools", "agent")

# Compile the graph
graph = builder.compile()
