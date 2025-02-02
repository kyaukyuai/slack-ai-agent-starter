"""Memory management functionality for the LangGraph implementation."""

from typing import Dict
from typing import List

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore


def load_memories(
    state: Dict[str, List[BaseMessage]], config: RunnableConfig, *, store: BaseStore
) -> Dict:
    """Load relevant memories for the current conversation."""
    user_id = config.get("configurable", {}).get("user_id", "langgraph-studio-user")
    namespace = ("memories", user_id)

    # Search for relevant memories based on the last message
    memories = store.search(namespace, query=str(state["messages"][-1].content))

    # Format memories with context
    recall_memories = [
        f"{memory.value.get('content', '')} - Context: {memory.value.get('context', '')}"
        for memory in memories
    ]

    return {
        "messages": state["messages"],
        "recall_memories": recall_memories,
    }
