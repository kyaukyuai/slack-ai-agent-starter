# Slack AI Agent Starter

A comprehensive toolkit for building and running AI-powered Slack bots using LangGraph and Slack Bolt API.

## Features

### 1. Conversation Capabilities
- Natural language interaction through mentions
- Context-aware responses using conversation history
- Thread-based communication management
- Interactive message components

### 2. Command System
- `help` - Display detailed usage instructions
- `ai [question]` - Direct interaction with AI agent
- `hello` - Interactive greeting with button interface

### 3. Core Functionalities
- Advanced natural language processing
- Conversation history consideration
- Interactive UI elements (buttons, etc.)
- Error handling and feedback
- Customizable workflows

## Setup

### Prerequisites
- Python 3.8+
- Poetry for dependency management
- Slack App credentials
- LangGraph setup

### Environment Variables
Create a `.env` file with the following:
```
SLACK_BOT_TOKEN=your-bot-token
SLACK_APP_TOKEN=your-app-token
LANGGRAPH_URL=your-langgraph-url
LANGGRAPH_TOKEN=your-langgraph-token
```

### Installation
1. Clone the repository
```bash
git clone https://github.com/yourusername/slack-ai-agent-starter.git
cd slack-ai-agent-starter
```

2. Install dependencies
```bash
poetry install
```

3. Start the bot
```bash
poetry run python -m slack_ai_agent
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
├── agents/          # AI agent implementation
├── slack/
│   ├── handler/     # Event, message, and action handlers
│   ├── app.py      # Main Slack app configuration
│   └── utils.py    # Utility functions
└── README.md
```

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
