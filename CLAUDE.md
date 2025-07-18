# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
```bash
# Start both LangGraph and Web servers
make dev

# Start servers separately
make dev-langgraph  # LangGraph on port 2024
make dev-web       # Web server on port 3000

# Monitor logs
make logs

# Stop all servers
make kill
```

### Code Quality
```bash
# Run all checks (recommended before commits)
make check

# Individual checks
make lint         # Ruff linter with auto-fix
make type-check   # MyPy type checking
make format       # Ruff formatter
make test         # Run tests with pytest
make test-cov     # Run tests with coverage report
make pre-commit   # Run pre-commit hooks
```

### Testing
```bash
# Run specific test
poetry run pytest tests/path/to/test.py -v

# Run tests matching pattern
poetry run pytest tests/ -k "test_pattern" -v

# Run with debugging output
poetry run pytest tests/ -v -s
```

## Architecture Overview

### Project Structure
This is a Slack AI Agent framework using LangGraph for workflow orchestration. The codebase follows a modular architecture with clear separation between Slack integration and AI agent logic.

### Key Components

1. **Slack Integration Layer** (`slack_ai_agent/slack/`)
   - `app.py`: Main Slack Bolt application with auto-reload support
   - `handler/`: Event handlers for messages, actions, and Slack events
   - Thread-based conversation management
   - Interactive UI elements (buttons, modals)

2. **Agent Layer** (`slack_ai_agent/agents/`)
   - Multiple specialized agents using LangGraph state machines:
     - `simple_agent.py`: Basic conversational agent
     - `research_agent.py`: Multi-step research with reflection
     - `deep_research_agent.py`: Complex report generation
     - `summarize_agent.py`: Content summarization
   - Each agent follows the pattern: State → Nodes → Graph → Conditional Routing

3. **Tools System** (`slack_ai_agent/agents/tools/`)
   - Modular tools created via factory pattern in `create_tools()`
   - Categories: Search (Tavily/Perplexity), Content (scraping), Integrations (Slack/GitHub), Utilities (memory/REPL)
   - Tools are conditionally loaded based on environment variables

4. **Memory System** (`slack_ai_agent/agents/tools/memory.py`)
   - Vector embeddings using OpenAI
   - Persistent storage via LangGraph store
   - Semantic search for contextual retrieval

5. **Prompts** (`slack_ai_agent/agents/prompts/`)
   - Externalized prompt templates
   - Task-specific prompts (planning, writing, grading)

### Development Principles

1. **Type Safety**: All functions must have type annotations and return types
2. **Documentation**: PEP257 docstrings required for all functions and classes
3. **Testing**: Use pytest exclusively (no unittest), tests in `./tests` with full annotations
4. **Code Style**: Ruff for linting/formatting, 88-char line length
5. **Error Handling**: Comprehensive error handling with user-friendly Slack messages

### Environment Configuration

Required environment variables (see `.env.example`):
- Slack: `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`
- AI: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- LangGraph: `LANGGRAPH_URL`, `LANGGRAPH_TOKEN`
- Optional: Various API keys for tools (Tavily, Firecrawl, etc.)

### Extending the System

1. **New Agent**: Create in `agents/` with LangGraph StateGraph pattern
2. **New Tool**: Add to `agents/tools/` and update `create_tools()`
3. **New Slack Command**: Add handler in `slack/handler/`
4. **New Prompt**: Add to `agents/prompts/`

### Deployment Notes

- Two-container Docker setup: web (port 3000) + langgraph (port 2024)
- Hot-reload enabled in development via Hupper
- Slack socket mode for real-time events
- LangGraph Studio integration via `langgraph.json`

### Output Language

- All output results should be in Japanese (日本語で出力すること)
