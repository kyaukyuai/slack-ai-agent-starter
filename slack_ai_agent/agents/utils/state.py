"""State management functionality for the agent implementation."""

from typing import List

from langchain_core.runnables import RunnableConfig
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.store.base import BaseStore

from .models import model
from .models import prompt
from .tools import create_tools


class State(MessagesState):
    """State class for managing conversation state with memory capabilities."""

    recall_memories: List[str]


def agent(state: State, config: RunnableConfig, *, store: BaseStore) -> State:
    """Process the current state and generate a response using the LLM.

    Args:
        state (State): The current state of the conversation
        config (RunnableConfig): Runtime configuration
        store (BaseStore): Memory storage backend

    Returns:
        State: Updated state with agent's response
    """
    bound = prompt | model.bind_tools(tools=create_tools(store=store))
    recall_str = (
        "<recall_memory>\n" + "\n".join(state["recall_memories"]) + "\n</recall_memory>"
    )
    prediction = bound.invoke(
        {
            "messages": state["messages"],
            "recall_memories": recall_str,
        }
    )
    return {
        "messages": [prediction],  # type: ignore
    }


def tools(state: State, config: RunnableConfig, *, store: BaseStore) -> ToolNode:
    """Create tool node with configured tools.

    Args:
        state (State): Current conversation state
        config (RunnableConfig): Runtime configuration
        store (BaseStore): Memory storage backend

    Returns:
        ToolNode: Configured tool node
    """
    return ToolNode(tools=create_tools(store=store))
