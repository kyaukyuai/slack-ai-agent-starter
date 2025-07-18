# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Slack AI Agent Starter Kit that provides a framework for building AI-powered Slack bots using LangGraph and Slack Bolt API. The project integrates multiple AI capabilities through LangGraph, supporting both OpenAI and Anthropic models.

## Development Commands

### Code Quality
```bash
make lint         # Run Ruff linter with auto-fix
make type-check   # Run mypy type checker
make format       # Format code with Ruff
make test         # Run pytest tests (from ./tests directory)
make test-cov     # Run tests with coverage report
make check        # Run all checks (lint, type-check, format, test, pre-commit)
```

### Running the Application
```bash
make dev          # Start both LangGraph (port 2024) and Web servers (port 3000)
make dev-langgraph # Start LangGraph server only
make dev-web      # Start Web server only
make logs         # Tail server log files
make kill         # Kill all development servers
```

### Testing Individual Components
```bash
# Run specific test file
PYTHONPATH=. poetry run pytest tests/test_specific.py -v

# Run tests with specific marker
PYTHONPATH=. poetry run pytest -m "not slow" -v
```

## Architecture

### Core Components

1. **LangGraph Server** (port 2024): Handles AI agent workflow orchestration
   - Configured via `langgraph.json`
   - Multiple specialized agents defined in `slack_ai_agent/agents/`

2. **Web Server** (port 3000): Manages Slack bot interactions
   - Entry point: `slack_ai_agent/slack/app.py`
   - Event handlers in `slack_ai_agent/slack/handler/`

### Agent Types and Locations
- **Simple Agent**: `agents/agent.py` - Basic conversational AI
- **Research Agents**: `agents/research_agent.py`, `agents/deep_research_agent.py` - Web research
- **PowerPoint Agents**: `agents/powerpoint_*.py` - Presentation generation
- **URL Research**: `agents/url_research/` - Advanced URL content analysis
- **News/Brief Agents**: `agents/news_frontpage_agent.py`, `agents/smart_brief_generation_agent.py`

### Key Design Patterns

1. **Type Annotations**: All functions must have type hints and PEP 257 docstrings
2. **Testing**: Use pytest exclusively (no unittest), tests go in `./tests/`
3. **Async Patterns**: Many Slack handlers and agent functions are async
4. **Tool-based Architecture**: Agents use tools defined in `agents/tools/`
5. **State Management**: LangGraph manages conversation state and workflow

## Environment Configuration

Required environment variables in `.env`:
```env
# Slack (required)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...

# AI Provider (choose one)
OPENAI_API_KEY=...
# or
ANTHROPIC_API_KEY=...

# LangGraph
LANGGRAPH_URL=...
LANGGRAPH_TOKEN=...

# Optional
TAVILY_API_KEY=...  # For search functionality
FIRECRAWL_API_KEY=...  # For web scraping
```

## Important Conventions

1. **Import Organization**: Group imports by standard library, third-party, and local
2. **Error Handling**: Use structured logging and user-friendly Slack messages
3. **File Structure**: Keep agents, tools, and utilities in separate modules
4. **Authentication**: Handled via `agents/security/auth.py`
5. **Slack Manifest**: Update `slack/manifest/manifest.yml` for new commands/features

## Common Development Tasks

### Adding a New Agent
1. Create agent file in `slack_ai_agent/agents/`
2. Define the graph workflow using LangGraph
3. Add to `langgraph.json` graphs section
4. Implement corresponding Slack handler if needed

### Adding a New Tool
1. Create tool in `slack_ai_agent/agents/tools/`
2. Follow the existing tool patterns (see `tavily_tool.py`, `firecrawl_tool.py`)
3. Import and bind to agents as needed

### Modifying Slack Interactions
1. Event handlers: `slack/handler/event_handler.py`
2. Message handlers: `slack/handler/message_handler.py`
3. Action handlers: `slack/handler/action_handler.py`
4. Update manifest if adding new slash commands or events

## Debugging Tips

- Check `langgraph.log` and `slack_bot.log` for server outputs
- Use `make logs` to tail both log files simultaneously
- LangGraph Studio available at http://localhost:2024 when running
- Enable debug logging by setting appropriate log levels in code
