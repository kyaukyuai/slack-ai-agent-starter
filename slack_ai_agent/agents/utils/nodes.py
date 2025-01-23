from typing import Dict
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode

from .tools import tools


tool_node = ToolNode(tools=tools)

model = ChatAnthropic(model="claude-3-5-sonnet-20240620").bind_tools(tools)  # type: ignore


def call_model(state: MessagesState) -> Dict[str, List[BaseMessage]]:
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}
