"""Memory management functionality for the agent implementation."""

from typing import Dict
from typing import List

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore


def load_memories(
    state: Dict[str, List[BaseMessage]], config: RunnableConfig, *, store: BaseStore
) -> Dict:
    """Load memories from storage using semantic search based on conversation context.

    Args:
        state (Dict[str, List[BaseMessage]]): Current conversation state
        config (RunnableConfig): Runtime configuration
        store (BaseStore): Memory storage backend with vector search capabilities

    Returns:
        Dict: Updated state with loaded memories and their relevance scores
    """
    namespace = ("memories", "langgraph-studio-user")

    # Use semantic search with the loading query
    memories = store.search(
        namespace,
        query=str(state["loading_query"]),
        filter={"type": "conversation"},
        limit=5,  # Limit to top 5 most relevant memories
    )

    # Format memories with relevance scores
    recall_memories = [
        f"Content: {memory.value.get('content', '')}\n"
        f"Context: {memory.value.get('context', '')}\n"
        f"(Author: {memory.value.get('author', 'Unknown')}, "
        f"Created: {memory.value.get('created_at', 'Unknown')})"
        for memory in memories
    ]

    return {
        "messages": state["messages"],
        "recall_memories": recall_memories,
    }
