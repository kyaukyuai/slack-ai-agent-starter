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

    Retrieves both query-relevant memories and recent memories regardless of query.

    Args:
        state (Dict[str, List[BaseMessage]]): Current conversation state
        config (RunnableConfig): Runtime configuration
        store (BaseStore): Memory storage backend with vector search capabilities

    Returns:
        Dict: Updated state with loaded memories and their relevance scores
    """
    namespace = ("memories", "langgraph-studio-user")
    recall_memories = []

    # Get recent memories by using a generic search
    # Since we can't use get_all directly, we'll use search with a generic query
    # that should match most content
    recent_memories = store.search(
        namespace,
        query="",  # Empty query to match all documents
        filter={"type": "conversation"},
        limit=25,  # Retrieve 25 most recent memories
    )

    # Format recent memories
    for memory in recent_memories:
        recall_memories.append(
            f"Recent Memory:\n"
            f"Content: {memory.value.get('content', '')}\n"
            f"Context: {memory.value.get('context', '')}\n"
            f"(Author: {memory.value.get('author', 'Unknown')}, "
            f"Created: {memory.value.get('created_at', 'Unknown')})"
        )

    # If there's a query, also get query-relevant memories
    if "loading_query" in state and state["loading_query"]:
        # Use semantic search with the loading query
        query_memories = store.search(
            namespace,
            query=str(state["loading_query"]),
            filter={"type": "conversation"},
            limit=25,  # Limit to top 25 most relevant memories
        )

        # Format query-relevant memories with high importance
        for memory in query_memories:
            recall_memories.append(
                f"Relevant Memory (Importance: HIGH):\n"
                f"Content: {memory.value.get('content', '')}\n"
                f"Context: {memory.value.get('context', '')}\n"
                f"(Author: {memory.value.get('author', 'Unknown')}, "
                f"Created: {memory.value.get('created_at', 'Unknown')})"
            )

    return {
        "messages": state["messages"],
        "recall_memories": recall_memories,
    }
