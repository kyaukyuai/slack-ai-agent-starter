"""Model related functionality for the agent implementation."""

from typing import Dict
from typing import List

from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import MessagesState
from langgraph.store.base import BaseStore

from ..tools import create_tools


# Initialize base model
model = ChatAnthropic(model="claude-3-5-sonnet-20241022")  # type: ignore

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
            " preferences and current emotional state.\n\n"
            "## Response Guidelines:\n"
            "- Use markdown formatting to improve readability\n"
            "- Avoid including timestamps in responses\n"
            "- Do not repeat similar responses\n"
            "- Use tools to persist information you want to retain\n"
            "- If calling tools, all text before the tool call is internal\n"
            "- Only respond AFTER tool calls complete successfully\n\n",
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


class State(MessagesState):
    """State class for managing conversation state with memory capabilities."""

    recall_memories: List[str]


def agent(state: State, config: RunnableConfig, *, store: BaseStore) -> State:
    """Process the current state and generate a response using the LLM.

    Args:
        state (State): The current state of the conversation
        config (RunnableConfig): Runtime configuration
        store (BaseStore): Memory storage backend

    Returns:
        State: Updated state with agent's response
    """
    bound = prompt | model.bind_tools(tools=create_tools())
    recall_str = (
        "<recall_memory>\n" + "\n".join(state["recall_memories"]) + "\n</recall_memory>"
    )
    prediction = bound.invoke(
        {
            "messages": state["messages"],
            "recall_memories": recall_str,
        }
    )
    return {
        "messages": [prediction],  # type: ignore
    }
