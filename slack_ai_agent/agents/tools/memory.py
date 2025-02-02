"""Memory-related tools for the LangGraph implementation."""

import uuid
from dataclasses import dataclass
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
    config: RunnableConfig,
    store: Annotated[Any, InjectedStore()],
) -> str:
    """Upsert a memory in the database."""
    if store is None:
        raise ValueError("Memory store is not configured")

    memory = Memory(
        content=content,
        context=context,
        id=memory_id or str(uuid.uuid4()),
    )

    user_id = get_user_id(config)
    store.put(
        ("memories", user_id),
        key=memory.id,
        value=memory.to_dict(),
    )

    return f"Stored memory: {content}"
