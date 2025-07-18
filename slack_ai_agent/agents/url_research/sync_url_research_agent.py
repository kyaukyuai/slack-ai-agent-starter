"""
URL Research Agent - Synchronous Version

This module provides a synchronous agent for researching URLs and generating structured reports.
It uses LangGraph to orchestrate the workflow and LangChain for LLM interactions.
"""

from slack_ai_agent.agents.url_research.graph_builder import build_graph


# Build the graph
graph = build_graph()

# Export the graph for use in other modules
__all__ = ["graph"]
