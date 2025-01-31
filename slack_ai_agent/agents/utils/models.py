"""Model related functionality for the agent implementation."""

from typing import Dict
from typing import List

from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from langchain_core.tools import Tool
from langgraph.prebuilt import ToolNode

from .tools import create_tools
from .tools import save_recall_memory
from .tools import search_recall_memories


# Initialize base model
model = ChatAnthropic(model="claude-3-5-sonnet-20241022")  # type: ignore

# Convert function tools to Tool instances
save_recall_tool = Tool.from_function(
    func=save_recall_memory,
    name="save_recall_memory",
    description="Save memory to vectorstore for later semantic retrieval.",
)

search_recall_tool = Tool.from_function(
    func=search_recall_memories,
    name="search_recall_memories",
    description="Search for relevant memories.",
)

# Define the prompt template for the agent
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant with advanced long-term memory"
            " capabilities. Powered by a stateless LLM, you must rely on"
            " external memory to store information between conversations."
            " Utilize the available memory tools to store and retrieve"
            " important details that will help you better attend to the user's"
            " needs and understand their context.\n\n"
            "Memory Usage Guidelines:\n"
            "1. Actively use memory tools (upsert_memory)"
            " to build a comprehensive understanding of the user.\n"
            "2. Make informed suppositions and extrapolations based on stored"
            " memories.\n"
            "3. Regularly reflect on past interactions to identify patterns and"
            " preferences.\n"
            "4. Update your mental model of the user with each new piece of"
            " information.\n"
            "5. Cross-reference new information with existing memories for"
            " consistency.\n"
            "6. Prioritize storing emotional context and personal values"
            " alongside facts.\n"
            "7. Use memory to anticipate needs and tailor responses to the"
            " user's style.\n"
            "8. Recognize and acknowledge changes in the user's situation or"
            " perspectives over time.\n"
            "9. Leverage memories to provide personalized examples and"
            " analogies.\n"
            "10. Recall past challenges or successes to inform current"
            " problem-solving.\n\n"
            "## Recall Memories\n"
            "Recall memories are contextually retrieved based on the current"
            " conversation:\n{recall_memories}\n\n"
            "## Instructions\n"
            "Engage with the user naturally, as a trusted colleague or friend."
            " There's no need to explicitly mention your memory capabilities."
            " Instead, seamlessly incorporate your understanding of the user"
            " into your responses. Be attentive to subtle cues and underlying"
            " emotions. Adapt your communication style to match the user's"
            " preferences and current emotional state. Use tools to persist"
            " information you want to retain in the next conversation. If you"
            " do call tools, all text preceding the tool call is an internal"
            " message. Respond AFTER calling the tool, once you have"
            " confirmation that the tool completed successfully.\n\n",
        ),
        ("placeholder", "{messages}"),
    ]
)


def call_model(state: Dict[str, List[BaseMessage]]) -> Dict[str, List[BaseMessage]]:
    """Process messages with the base model.

    Args:
        state (Dict[str, List[BaseMessage]]): Current conversation state

    Returns:
        Dict[str, List[BaseMessage]]: Updated state with model response
    """
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def create_memory_model(store):
    """Create a model instance with memory capabilities.

    Args:
        store: Memory storage backend

    Returns:
        Model instance configured with memory tools
    """
    base_model = ChatAnthropic(model="claude-3-5-sonnet-20241022")  # type: ignore
    memory_tools = create_tools(store=store)
    return base_model.bind_tools(tools=memory_tools)


tool_node = ToolNode(tools=create_tools())
