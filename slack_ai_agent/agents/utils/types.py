"""Type definitions for the agent implementation."""

from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import TypedDict

from langchain_core.messages import BaseMessage


class MessagesState(TypedDict):
    """State containing messages and their context."""

    messages: List[BaseMessage]
    config: Dict[str, Any]


class GraphConfig(TypedDict):
    """Configuration for the agent graph."""

    model_name: Literal["anthropic", "openai"]
