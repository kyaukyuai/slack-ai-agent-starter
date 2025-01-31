import os
import uuid
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from langchain.schema import Document
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langgraph.store.base import BaseStore


def get_user_id(config: Optional[RunnableConfig] = None) -> str:
    """Get user ID from config or return default.

    Args:
        config (Optional[RunnableConfig]): Runtime configuration

    Returns:
        str: User ID string

    Raises:
        ValueError: If user ID is None in config
    """
    if config is None:
        return "langgraph-studio-user"

    config_dict = config.get("configurable", {})
    user_id = config_dict.get("user_id", "langgraph-studio-user")
    if user_id is None:
        raise ValueError("User ID needs to be provided to save a memory.")

    return user_id


@dataclass
class Memory:
    """Memory data structure."""

    content: str
    context: str
    id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary format.

        Returns:
            Dict[str, Any]: Dictionary representation of memory
        """
        return {
            "content": self.content,
            "context": self.context,
        }


class UpsertMemoryTool(BaseTool):
    """Tool for upserting memories in the database."""

    name = "upsert_memory"
    description = """Upsert a memory in the database. If a memory conflicts with an existing one,
    then just UPDATE the existing one by passing in memory_id. If the user corrects a memory, UPDATE it.

    Args:
        content: The main content of the memory (e.g. "User expressed interest in learning about French.")
        context: Additional context (e.g. "This was mentioned while discussing career options in Europe.")
        memory_id: ONLY PROVIDE IF UPDATING AN EXISTING MEMORY.
    """
    store: Optional[BaseStore] = None

    def __init__(self, store: Optional[BaseStore] = None) -> None:
        """Initialize UpsertMemoryTool.

        Args:
            store (Optional[BaseStore]): Storage backend for memories
        """
        super().__init__()
        self.store = store

    def _run(
        self,
        content: str,
        context: str,
        memory_id: Optional[str] = None,
        config: Optional[RunnableConfig] = None,
    ) -> str:
        """Execute memory upsert operation.

        Args:
            content (str): Main memory content
            context (str): Additional context
            memory_id (Optional[str]): ID for updating existing memory
            config (Optional[RunnableConfig]): Runtime configuration

        Returns:
            str: Confirmation message

        Raises:
            ValueError: If store is not configured
        """
        if self.store is None:
            raise ValueError("store is required")

        memory = Memory(
            content=content,
            context=context,
            id=memory_id or str(uuid.uuid4()),
        )

        user_id = get_user_id(config)
        self.store.put(
            ("memories", user_id),
            key=memory.id,
            value=memory.to_dict(),
        )
        return f"Stored memory: {content}"


# Initialize vector store for semantic search
recall_vector_store = InMemoryVectorStore(OpenAIEmbeddings())


@tool
def save_recall_memory(memory: str, config: RunnableConfig) -> str:
    """Save memory to vectorstore for later semantic retrieval.

    Args:
        memory (str): Memory content to save
        config (RunnableConfig): Runtime configuration

    Returns:
        str: Saved memory content
    """
    user_id = get_user_id(config)
    document = Document(
        page_content=memory, id=str(uuid.uuid4()), metadata={"user_id": user_id}
    )
    recall_vector_store.add_documents([document])
    return memory


@tool
def search_recall_memories(query: str, config: RunnableConfig) -> List[str]:
    """Search for relevant memories.

    Args:
        query (str): Search query
        config (RunnableConfig): Runtime configuration

    Returns:
        List[str]: List of relevant memory contents
    """
    user_id = get_user_id(config)

    def _filter_function(doc: Document) -> bool:
        return doc.metadata.get("user_id") == user_id

    documents = recall_vector_store.similarity_search(
        query, k=3, filter=_filter_function
    )
    return [document.page_content for document in documents]


def create_tools(store: Optional[BaseStore] = None) -> List[BaseTool]:
    """Create a list of tools with optional store configuration.

    Args:
        store (Optional[BaseStore]): The store to use for memory operations

    Returns:
        List[BaseTool]: List of configured tools
    """
    tools: List[BaseTool] = []

    if os.getenv("TAVILY_API_KEY"):
        tools.append(TavilySearchResults(max_results=3))

    if store is not None:
        tools.append(UpsertMemoryTool(store=store))

    return tools
