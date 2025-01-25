.PHONY: pre-commit lint type-check format test test-cov dev dev-langgraph dev-web kill help check logs

# 定数定義
CURRENT_DIR := $(shell pwd)
LANGGRAPH_PORT := 2024
WEB_PORT := 3000

# 開発環境のセットアップとチェック
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

# 開発サーバー起動
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
	make dev-langgraph > langgraph.log 2>&1 & make dev-web > web.log 2>&1 & < /dev/null &
	@echo "Servers started in background. Check langgraph.log and web.log for output"
	@echo "Use 'make logs' to tail the log files"
	@echo "Use 'make kill' to stop the servers"

# ログ監視
logs:
	@echo "Tailing log files..."
	tail -f langgraph.log web.log

# プロセス管理
kill:
	@echo "Killing development servers..."
	@lsof -ti:${LANGGRAPH_PORT} | xargs kill -9 2>/dev/null || true
	@lsof -ti:${WEB_PORT} | xargs kill -9 2>/dev/null || true
	@rm -f langgraph.log web.log
	@echo "Servers stopped and log files removed"

# ヘルプ
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
