.PHONY: pre-commit lint type-check format test test-cov dev dev-langgraph dev-web kill help check logs

# Constants
CURRENT_DIR := $(shell pwd)
LANGGRAPH_PORT := 2024
WEB_PORT := 3000

# Development environment setup and checks
lint:
	@echo "Running Ruff linter..."
	poetry run ruff check . --fix

type-check:
	@echo "Running mypy type checker..."
	poetry run mypy . --config-file=pyproject.toml

format:
	@echo "Formatting code with Ruff..."
	poetry run ruff format .

pre-commit:
	@echo "Running pre-commit checks..."
	poetry run pre-commit run --all-files

test:
	@echo "Running tests..."
	PYTHONPATH=${CURRENT_DIR} poetry run pytest tests/ -v

test-cov:
	@echo "Running tests with coverage..."
	PYTHONPATH=${CURRENT_DIR} poetry run pytest tests/ -v --cov=slack_ai_agent --cov-report=term-missing

check: lint type-check format test pre-commit
	@echo "All checks passed!"

# Development server startup
dev-langgraph:
	@echo "Starting LangGraph server on port ${LANGGRAPH_PORT}..."
	poetry run langgraph dev --host localhost --port ${LANGGRAPH_PORT}

dev-web:
	@echo "Starting Web server on port ${WEB_PORT}..."
	PYTHONPATH=${PYTHONPATH}:${CURRENT_DIR} PORT=${WEB_PORT} HUPPER_NO_STDIN_FILENO=1 poetry run python slack_ai_agent/slack/app.py --host localhost < /dev/null

dev:
	@echo "Starting development servers..."
	@echo "LangGraph will be available at http://localhost:${LANGGRAPH_PORT}"
	@echo "Web server will be available at http://localhost:${WEB_PORT}"
	make dev-langgraph > langgraph.log 2>&1 & make dev-web > slack_bot.log 2>&1 & < /dev/null &
	@echo "Servers started in background. Check langgraph.log and slack_bot.log for output"
	@echo "Use 'make logs' to tail the log files"
	@echo "Use 'make kill' to stop the servers"

# Log monitoring
logs:
	@echo "Tailing log files..."
	tail -f langgraph.log slack_bot.log

# Process management
kill: kill-dev-web kill-dev-langgraph
	@echo "All development servers stopped and log files removed"

kill-dev-web:
	@echo "Killing web server..."
	@lsof -ti:${WEB_PORT} | xargs kill -9 2>/dev/null || true
	@rm -f slack_bot.log
	@echo "Web server stopped and log file removed"

kill-dev-langgraph:
	@echo "Killing langgraph server..."
	@lsof -ti:${LANGGRAPH_PORT} | xargs kill -9 2>/dev/null || true
	@rm -f langgraph.log
	@echo "LangGraph server stopped and log file removed"

# Help
help:
	@echo "Available commands:"
	@echo "Code Quality:"
	@echo "  make lint         - Run Ruff linter"
	@echo "  make type-check   - Run mypy type checker"
	@echo "  make format       - Format code with Ruff"
	@echo "  make pre-commit   - Run pre-commit checks"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make check        - Run all checks (lint, type-check, format, test, pre-commit)"
	@echo ""
	@echo "Development Servers:"
	@echo "  make dev          - Start both LangGraph and Web servers in background"
	@echo "  make dev-langgraph - Start LangGraph server only"
	@echo "  make dev-web      - Start Web server only"
	@echo ""
	@echo "Utilities:"
	@echo "  make logs         - Tail both server log files"
	@echo "  make kill         - Kill all development servers and remove log files"
	@echo "  make kill-dev-web - Kill web server only and remove its log file"
	@echo "  make kill-dev-langgraph - Kill LangGraph server only and remove its log file"
