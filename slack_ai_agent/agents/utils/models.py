"""Model related functionality for the agent implementation."""

from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

import pytz  # type: ignore
from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import MessagesState
from langgraph.store.base import BaseStore


def get_current_jst_time() -> str:
    """Get the current time in JST format.

    Returns:
        str: Current time in JST format (YYYY/MM/DD HH:MM:SS)
    """
    jst = pytz.timezone("Asia/Tokyo")
    current_time = datetime.now(jst)
    return current_time.strftime("%Y/%m/%d %H:%M:%S")


# Initialize base model
model = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens_to_sample=64_000)  # type: ignore

# Define the prompt template for the agent
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"Current time (JST): {get_current_jst_time()}\n\n"
            "You are a helpful assistant with advanced long-term memory"
            " capabilities and research abilities. Powered by a stateless LLM, you must rely on"
            " external memory to store information between conversations and"
            " the research tool to gather comprehensive information."
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
            "Deep Research Usage Guidelines:\n"
            "1. ALWAYS maintain the following structure when presenting deep research results:\n"
            "   ```markdown\n"
            "   # [Research Topic]\n\n"
            "   [Contextual introduction if needed]\n\n"
            "   ## [Section Title]\n"
            "   [Section content with detailed information]\n\n"
            "   ### Sources:\n"
            "   * [Link 1: https://example.com/source1]\n"
            "   * [Link 2: https://example.com/source2]\n\n"
            "   ## [Section Title]\n"
            "   [Section content with detailed information]\n\n"
            "   ### Sources:\n"
            "   * [Link 1: https://example.com/source1]\n"
            "   * [Link 2: https://example.com/source2]\n\n"
            "   ## Key Findings\n"
            "   [Summary of main insights and takeaways]\n\n"
            "   ```\n"
            "2. Content organization requirements:\n"
            "   - Follow proper hierarchical formatting with headers and subheaders\n"
            "   - Ensure logical structure and flow between sections\n"
            "   - Use tables for comparative data when appropriate\n"
            "   - Include section references when citing specific information\n"
            "   - ALWAYS include a Sources section after each main section with all source URLs as bullet points\n"
            "   - Sources must contain full URLs (e.g., https://example.com/article) not just names or descriptions\n"
            "3. Integration guidelines:\n"
            "   - Present comprehensive information from deep_research.result.report\n"
            "   - Structure the response to follow the report's section organization\n"
            "   - Preserve formatting elements like tables, bullet points, and emphasis\n"
            "   - Maintain the professional tone and depth of the original report\n"
            "   - Ensure all source links are properly formatted and working\n"
            "   - Source links must include full URLs (e.g., https://example.com/article)\n"
            "4. Visual presentation:\n"
            "   - Use markdown formatting to enhance readability\n"
            "   - Apply consistent formatting for section headers\n"
            "   - Ensure proper spacing between sections\n"
            "   - Preserve tables, lists, and other structured elements\n\n"
            "CRITICAL: When presenting deep_research results, you MUST preserve ALL Sources sections exactly as provided. Never summarize, truncate, or omit the Sources sections that appear after each main section. Each main section MUST be followed by its corresponding Sources section containing the full URLs.\n\n"
            "Summarize Usage Guidelines:\n"
            "1. ALWAYS maintain the following structure when using summarize tool:\n"
            "   ```markdown\n"
            "   [Your contextual introduction if needed]\n\n"
            "   ## Content Summary\n"
            "   [Integrate summarize.result.summary here]\n\n"
            "   ### Source:\n"
            "   * [The URL that was summarized]\n"
            "   ```\n"
            "2. Format requirements for summarize responses:\n"
            "   - Never omit the Source section\n"
            "   - Present the source URL as a bullet point\n"
            "   - Maintain clear separation between summary and source\n"
            "3. Integration guidelines:\n"
            "   - Synthesize summarize.result.summary into your response\n"
            "   - Always append the source URL at the end\n"
            "   - Cross-reference findings with existing memories\n"
            "   - Store key findings in memory for future reference\n"
            "4. Content organization:\n"
            "   - Use clear section headers\n"
            "   - Structure information logically\n"
            "   - Support all claims with the provided content\n\n"
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
            "- Only respond AFTER tool calls complete successfully\n"
            "- Summarize responses MUST include Content Summary and Source sections\n"
            "- Deep Research responses MUST follow the report's section structure\n"
            "- Deep Research responses MUST include Sources sections after each main section\n"
            "- NEVER omit or remove Sources sections from deep_research results\n"
            "- When presenting research results, preserve Sources sections exactly as provided\n"
            "- Ensure exact correspondence between tool output and response structure\n\n",
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
    loading_query: Optional[str]


def agent(state: State, config: RunnableConfig, *, store: BaseStore) -> State:
    """Process the current state and generate a response using the LLM.

    Args:
        state (State): The current state of the conversation
        config (RunnableConfig): Runtime configuration
        store (BaseStore): Memory storage backend

    Returns:
        State: Updated state with agent's response
    """
    # Import here to avoid circular import
    from ..tools.create_tools import create_tools

    bound = prompt | model.bind_tools(tools=create_tools())

    messages = [msg for msg in state["messages"] if msg.content]

    recall_str = (
        "<recall_memory>\n" + "\n".join(state["recall_memories"]) + "\n</recall_memory>"
    )
    prediction = bound.invoke(
        {
            "messages": messages,
            "recall_memories": recall_str,
        }
    )
    return {
        "messages": [prediction],  # type: ignore
        "recall_memories": state["recall_memories"],
    }
