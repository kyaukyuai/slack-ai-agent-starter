"""Memory-related tools for the LangGraph implementation with semantic search capabilities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langgraph.prebuilt import InjectedStore


@dataclass
class Memory:
    """Memory data structure with vector embedding support."""

    content: str
    context: str
    id: str = ""
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary format."""
        return {
            "content": self.content,
            "context": self.context,
            "embedding": self.embedding,
            "text": f"{self.content}\n\nContext: {self.context}",  # Combined text for embedding
        }


# Initialize embeddings model
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")


def get_user_id(config: Optional[RunnableConfig] = None) -> str:
    """Get user ID from config or return default."""
    if config is None:
        return "langgraph-studio-user"

    config_dict = config.get("configurable", {})
    user_id = config_dict.get("user_id", "langgraph-studio-user")

    if user_id is None:
        raise ValueError("User ID needs to be provided to save a memory.")
    return user_id


@tool
def upsert_memory(
    content: str,
    context: str,
    memory_id: Optional[str],
    author: Optional[str] = None,
    created_at: Optional[str] = None,
    *,
    config: RunnableConfig,
    store: Annotated[Any, InjectedStore()],
) -> str:
    """Upsert a memory in the database with vector embedding support.

    If a memory conflicts with an existing one, then just UPDATE the
    existing one by passing in memory_id - don't create two memories
    that are the same. If the user corrects a memory, UPDATE it.

    Args:
        content: The main content of the memory
        context: The context in which the memory was created
        memory_id: Optional ID for the memory, will be generated if not provided
        author: Optional author override
        created_at: Optional timestamp for when memory was created
    """
    if store is None:
        raise ValueError("Memory store is not configured")

    # Create combined text for embedding
    combined_text = f"{content}\n\nContext: {context}"

    # Generate embedding
    embedding = embeddings_model.embed_query(combined_text)

    memory = Memory(
        content=content,
        context=context,
        id=memory_id or str(uuid.uuid4()),
        embedding=embedding,
    )

    # Get user ID from config if not explicitly provided
    memory_author = author or get_user_id(config)
    memory_created_at = created_at or datetime.now().isoformat()

    # Build complete memory dict with additional fields
    memory_dict = memory.to_dict()
    memory_dict["author"] = memory_author
    memory_dict["created_at"] = memory_created_at
    memory_dict["type"] = "conversation"  # Add type for filtering in search

    # Store with vector search support
    store.put(
        ("memories", "langgraph-studio-user"),
        key=memory.id,
        value=memory_dict,
        index=["text"],  # Enable semantic search on the text field
    )

    return f"Stored memory with vector embedding: {content}"


def search_memories(state: Dict[str, Any], *, store: Any) -> Dict[str, List[str]]:
    """Search for relevant memories using semantic search.

    Args:
        state: The current conversation state
        store: The memory store

    Returns:
        Dict containing list of relevant memories
    """
    if not state.get("loading_query"):
        return {"recall_memories": []}

    # Search for relevant memories using the loading query
    results = store.search(
        ("memories", "langgraph-studio-user"),
        query=state["loading_query"],
        filter={"type": "conversation"},
        limit=5,  # Retrieve top 5 most relevant memories
    )

    # Format results with relevance scores
    memories = [
        f"Previous memory ({r.score:.2f} relevance):\n{r.value['content']}\nContext: {r.value['context']}"
        for r in results
    ]

    return {"recall_memories": memories}
