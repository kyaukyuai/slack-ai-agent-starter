# Slack AI Agent

This package implements a Slack bot with integrated AI agent capabilities using LangGraph and LangChain.

## Structure

```
slack-ai-agent/
├── agents/
│   ├── __init__.py
│   ├── simple_agent.py    # LangGraph AI agent implementation
│   └── utils/
│       ├── __init__.py
│       ├── nodes.py       # Agent workflow nodes
│       └── types.py       # Type definitions
└── slack/
    ├── __init__.py
    ├── app.py            # Main Slack bot application
    └── bot_handler.py    # Integration between Slack and AI agent
```

## Features

- Basic Slack bot functionality:
  - Responds to "hello" messages with an interactive button
  - Handles button click events
- AI agent integration:
  - Processes messages prefixed with "ai"
  - Uses LangGraph for workflow management
  - Supports both OpenAI and Anthropic models
  - Handles tool execution and complex interactions

## Prerequisites

- Python 3.11 or higher
- Poetry for dependency management
- Slack App credentials
- OpenAI API key (or Anthropic API key if using Claude)

## Setup

1. Set up environment variables in `.env`:
   ```
   # Slack Configuration
   SLACK_BOT_TOKEN=your-bot-token
   SLACK_SIGNING_SECRET=your-signing-secret
   PORT=3000  # Optional, defaults to 3000

   # AI Configuration
   OPENAI_API_KEY=your-openai-api-key
   # Or for Anthropic:
   # ANTHROPIC_API_KEY=your-anthropic-api-key
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Run the Slack bot:
   ```bash
   poetry run python -m slack-ai-agent.slack.app
   ```

## Interacting with the Bot

- Send "hello" to get a greeting with an interactive button
- Send a message starting with "ai" to interact with the AI agent
  Example: "ai what's the weather like?"

The AI agent will process your message using either GPT-3.5-turbo or Claude-3, depending on the configuration.

## Development

The implementation follows these principles:
- Type hints and docstrings for all functions and classes
- Modular design with separate packages for Slack bot and AI agent
- Clear separation of concerns between bot handling and AI processing
- Integration with modern AI tools:
  - LangGraph for workflow management
  - LangChain for AI model integration
  - Support for both OpenAI and Anthropic models

## Dependencies

Key dependencies include:
- `slack-bolt`: For Slack bot functionality
- `langgraph`: For AI agent workflow management
- `langchain_core`: Core LangChain functionality
- `langchain_openai`: OpenAI model integration
- `langchain_anthropic`: Anthropic model integration
- `python-dotenv`: For environment variable management

For development:
- `ruff`: For code linting
- `mypy`: For type checking
- `pre-commit`: For git hooks
- `langgraph-cli`: For development tools

## Error Handling

The implementation includes comprehensive error handling:
- Graceful handling of API errors
- Detailed logging for debugging
- User-friendly error messages in Slack
- Tool execution result reporting

## Extending the Agent

To add new capabilities:
1. Define new tool functions in `agents/utils/nodes.py`
2. Update the agent workflow in `agents/simple_agent.py`
3. Add any new environment variables to `.env`
4. Update type definitions in `agents/utils/types.py` if needed
