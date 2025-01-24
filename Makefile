.PHONY: pre-commit dev dev-langgraph dev-web kill help check logs

# 定数定義
CURRENT_DIR := $(shell pwd)
LANGGRAPH_PORT := 2024
WEB_PORT := 3000

# 開発環境のセットアップとチェック
pre-commit:
	@echo "Running pre-commit checks..."
	poetry run pre-commit run --all-files

check: pre-commit
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
	@echo "  make pre-commit  - Run pre-commit checks"
	@echo "  make check       - Run all checks (includes pre-commit)"
	@echo "  make dev         - Start both LangGraph and Web servers in background"
	@echo "  make dev-langgraph - Start LangGraph server only"
	@echo "  make dev-web     - Start Web server only"
	@echo "  make logs        - Tail both server log files"
	@echo "  make kill        - Kill all development servers and remove log files"
