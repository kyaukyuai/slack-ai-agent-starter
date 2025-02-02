"""Memory-related tools for the LangGraph implementation."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from typing import Any
from typing import Dict
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedStore


@dataclass
class Memory:
    """Memory data structure."""

    content: str
    context: str
    id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary format."""
        return {
            "content": self.content,
            "context": self.context,
        }


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
    """Upsert a memory in the database.

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

    memory = Memory(
        content=content,
        context=context,
        id=memory_id or str(uuid.uuid4()),
    )

    # Get user ID from config if not explicitly provided
    memory_author = author or get_user_id(config)
    memory_created_at = created_at or datetime.now().isoformat()

    # Build complete memory dict with additional fields
    memory_dict = memory.to_dict()
    memory_dict["author"] = memory_author
    memory_dict["created_at"] = memory_created_at

    store.put(
        ("memories", "langgraph-studio-user"),
        key=memory.id,
        value=memory_dict,
    )

    return f"Stored memory: {content}"
