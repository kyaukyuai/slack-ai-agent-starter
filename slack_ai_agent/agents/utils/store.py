"""Memory management functionality for the agent implementation."""

from typing import Dict
from typing import List

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore


def load_memories(
    state: Dict[str, List[BaseMessage]], config: RunnableConfig, *, store: BaseStore
) -> Dict:
    """Load memories from storage based on conversation context.

    Args:
        state (Dict[str, List[BaseMessage]]): Current conversation state
        config (RunnableConfig): Runtime configuration
        store (BaseStore): Memory storage backend

    Returns:
        Dict: Updated state with loaded memories
    """
    user_id = config.get("configurable", {}).get("user_id", "langgraph-studio-user")
    namespace = ("memories", user_id)
    memories = store.search(
        namespace, query=str(state["messages"][-1].content), limit=100
    )
    recall_memories = [
        f"{memory.value.get('content', '')} - Context: {memory.value.get('context', '')} "
        f"(Author: {memory.value.get('author', 'Unknown')}, "
        f"Created: {memory.value.get('created_at', 'Unknown')})"
        for memory in memories
    ]
    return {  # type: ignore
        "messages": state["messages"],
        "recall_memories": recall_memories,
    }
