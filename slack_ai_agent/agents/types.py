"""Type definitions for the agent implementation."""

from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import TypedDict

from langchain_core.messages import BaseMessage


class MessagesState(TypedDict):
    """State containing messages and their context."""

    messages: List[BaseMessage]
    config: Dict[str, Any]


class State(MessagesState):
    """State class for managing conversation state with memory capabilities."""

    recall_memories: List[str]


class GraphConfig(TypedDict):
    """Configuration for the agent graph."""

    model_name: Literal["anthropic", "openai"]


class UserConfig(TypedDict, total=False):
    """User configuration for the agent.

    Attributes:
        user_id: Slack user ID
        team_id: Slack team ID
        channel_id: Slack channel ID
        preferences: Optional user preferences
    """

    user_id: str
    team_id: Optional[str]
    channel_id: Optional[str]
    preferences: Optional[Dict[str, Any]]


class ToolCallArguments(TypedDict, total=False):
    """Arguments for tool calls.

    Attributes:
        content: Main content for the memory
        context: Additional context information
        memory_id: Optional ID for updating existing memory
    """

    content: str
    context: str
    memory_id: Optional[str]
