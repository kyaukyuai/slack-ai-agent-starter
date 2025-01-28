"""Memory management functionality for the agent implementation."""

import uuid
from typing import Dict
from typing import List

import tiktoken
from langchain.schema import get_buffer_string
from langchain_core.messages import BaseMessage
from langchain_core.messages import SystemMessage
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from .models import model
from .models import search_recall_tool
from .tools import UpsertMemoryTool
from .tools import create_tools


# Initialize tokenizer
tokenizer = tiktoken.encoding_for_model("gpt-4o")


def load_memories(state: Dict[str, List[BaseMessage]], config: RunnableConfig) -> Dict:
    """Load relevant memories for the current conversation.

    Args:
        state (Dict[str, List[BaseMessage]]): Current conversation state
        config (RunnableConfig): Runtime configuration

    Returns:
        Dict: Updated state with loaded memories
    """
    convo_str = get_buffer_string(state["messages"])
    convo_str = tokenizer.decode(tokenizer.encode(convo_str)[:2048])
    recall_memories = search_recall_tool.run(convo_str, config=config)
    return {  # type: ignore
        "messages": state["messages"],
        "recall_memories": recall_memories,
    }


def load_memories_from_store(
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
    memories = store.search(namespace, query=str(state["messages"][-1].content))
    recall_memories = [
        f"{memory.value.get('content', '')} - Context: {memory.value.get('context', '')}"
        for memory in memories
    ]
    return {  # type: ignore
        "messages": state["messages"],
        "recall_memories": recall_memories,
    }


def store_memory(
    state: Dict[str, List[BaseMessage]], config: RunnableConfig, store: BaseStore
) -> Dict[str, BaseMessage]:
    """Store memory from the current conversation.

    Args:
        state (Dict[str, List[BaseMessage]]): Current conversation state
        config (RunnableConfig): Runtime configuration
        store (BaseStore): Memory storage backend

    Returns:
        Dict[str, BaseMessage]: Updated state with tool message
    """
    last_message = state["messages"][-1]
    if not isinstance(last_message, BaseMessage):
        return {"messages": last_message}

    tool_calls = last_message.additional_kwargs.get("tool_calls", [])
    if not tool_calls:
        return {"messages": last_message}

    memory_tools = create_tools(store=store)
    memory_tool = next(
        (tool for tool in memory_tools if isinstance(tool, UpsertMemoryTool)), None
    )

    if not memory_tool:
        return {"messages": last_message}

    save_memories = []
    for tool_call in tool_calls:
        content = tool_call["args"]["content"]
        context = tool_call["args"]["context"]
        save_memories.append(memory_tool.run(content, context, config=config))

    results = [
        ToolMessage(
            content=str(memory[0]),
            tool_call_id=tool_call["id"],
        )
        for memory, tool_call in zip(save_memories, tool_calls)
        if memory
    ]

    return {"messages": results[0] if results else last_message}


def call_model_with_tool_call(
    state: Dict[str, List[BaseMessage]], config: RunnableConfig, *, store: BaseStore
) -> Dict[str, BaseMessage]:
    """Call model with memory context and handle tool calls.

    Args:
        state (Dict[str, List[BaseMessage]]): Current conversation state
        config (RunnableConfig): Runtime configuration
        store (BaseStore): Memory storage backend

    Returns:
        Dict[str, BaseMessage]: Updated state with model response
    """
    user_id = config.get("configurable", {}).get("user_id", "langgraph-studio-user")
    namespace = ("memories", user_id)
    memories = store.search(namespace, query=str(state["messages"][-1].content))
    info = "\n".join([d.value.get("data", "") for d in memories])
    system_msg = f"You are a helpful assistant talking to the user. User info: {info}"

    last_message = state["messages"][-1]
    if isinstance(last_message.content, str):
        if "remember" in last_message.content.lower():
            memory = "User name is Bob"
            store.put(namespace, str(uuid.uuid4()), {"data": memory})

    messages = state["messages"]
    system_message = SystemMessage(content=system_msg)
    response = model.invoke([system_message] + messages)  # type: ignore
    return {"messages": response}
