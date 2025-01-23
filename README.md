# Slack AI Agent Starter

A comprehensive toolkit for building and running AI-powered Slack bots using LangGraph and Slack Bolt API. This implementation integrates advanced AI capabilities through LangGraph and LangChain, supporting both OpenAI and Anthropic models.

## Features

### 1. Conversation Capabilities
- Natural language interaction through mentions
- Context-aware responses using conversation history
- Thread-based communication management
- Interactive message components
- Support for both OpenAI and Anthropic models

### 2. Command System
- `help` - Display detailed usage instructions
- `ai [question]` - Direct interaction with AI agent
- `hello` - Interactive greeting with button interface

### 3. Core Functionalities
- Advanced natural language processing with LangGraph and LangChain
- Conversation history consideration
- Interactive UI elements (buttons, etc.)
- Comprehensive error handling and feedback
- Customizable workflows
- Tool execution and complex interactions

## Prerequisites

- Python 3.11 or higher
- Poetry for dependency management
- Slack App credentials
- OpenAI API key (or Anthropic API key if using Claude)
- LangGraph setup

## Setup

### Environment Variables
Create a `.env` file with the following:
```env
# Slack Configuration
SLACK_BOT_TOKEN=your-bot-token
SLACK_APP_TOKEN=your-app-token
SLACK_SIGNING_SECRET=your-signing-secret
PORT=3000  # Optional, defaults to 3000

# AI Configuration
OPENAI_API_KEY=your-openai-api-key
# Or for Anthropic:
# ANTHROPIC_API_KEY=your-anthropic-api-key

# LangGraph Configuration
LANGGRAPH_URL=your-langgraph-url
LANGGRAPH_TOKEN=your-langgraph-token
```

### Installation
1. Clone the repository
```bash
git clone https://github.com/kyaukyuai/slack-ai-agent-starter.git
cd slack-ai-agent-starter
```

2. Install dependencies
```bash
poetry install
```

3. Start the development servers
```bash
# Start both LangGraph and Web servers
make dev

# Or start them separately
make dev-langgraph  # For LangGraph server
make dev-web        # For Web server
```

## Usage

### Basic Interaction
- Mention the bot: `@AI Assistant hello`
- Use direct commands: `ai what's the weather?`
- Get help: `help`

### Best Practices
1. Use threads for related conversations
2. Be specific with questions
3. Provide context when needed
4. Use appropriate commands for different tasks

## Project Structure
```
slack_ai_agent/
├── agents/                # AI agent implementation
│   ├── simple_agent.py   # LangGraph AI agent implementation
│   ├── security/         # Security-related functionality
│   └── utils/
│       ├── nodes.py      # Agent workflow nodes
│       ├── tools.py      # Tool implementations
│       └── types.py      # Type definitions
├── slack/
│   ├── handler/          # Event, message, and action handlers
│   ├── app.py           # Main Slack app configuration
│   └── utils.py         # Utility functions
└── README.md
```

## Development

### Key Dependencies
- `slack-bolt`: For Slack bot functionality
- `langgraph`: For AI agent workflow management
- `langchain_core`: Core LangChain functionality
- `langchain_openai`: OpenAI model integration
- `langchain_anthropic`: Anthropic model integration
- `python-dotenv`: For environment variable management

### Development Tools
- `ruff`: For code linting
- `mypy`: For type checking
- `pre-commit`: For git hooks
- `langgraph-cli`: For development tools

### Development Principles
- Type hints and docstrings for all functions and classes
- Modular design with separate packages for Slack bot and AI agent
- Clear separation of concerns between bot handling and AI processing
- Comprehensive error handling and logging

### Error Handling
The implementation includes:
- Graceful handling of API errors
- Detailed logging for debugging
- User-friendly error messages in Slack
- Tool execution result reporting

### Extending the Agent
To add new capabilities:
1. Define new tool functions in `agents/utils/nodes.py`
2. Update the agent workflow in `agents/simple_agent.py`
3. Add any new environment variables to `.env`
4. Update type definitions in `agents/utils/types.py` if needed

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
