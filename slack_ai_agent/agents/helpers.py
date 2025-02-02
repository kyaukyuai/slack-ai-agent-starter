"""Utility functions for the LangGraph implementation."""

from typing import Any
from typing import Dict
from typing import Optional

from langchain_core.runnables import RunnableConfig


def get_config_value(
    config: Optional[RunnableConfig], key: str, default: Any = None
) -> Any:
    """Get a value from the config or return default."""
    if config is None:
        return default

    config_dict = config.get("configurable", {})
    return config_dict.get(key, default)


def format_memory_content(memory: Dict[str, Any], include_context: bool = True) -> str:
    """Format memory content with optional context."""
    content = memory.get("content", "")
    if not include_context:
        return content

    context = memory.get("context", "")
    return f"{content} - Context: {context}"
