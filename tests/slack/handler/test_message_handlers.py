"""Test module for Slack message handlers."""

import re
from typing import Any
from typing import Dict

from _pytest.logging import LogCaptureFixture
from langchain_core.messages import AIMessage
from pytest_mock import MockerFixture

from slack_ai_agent.slack.handler.message_handlers import setup_message_handlers


def test_handle_hello_message(
    mock_app: Any,
    mock_handlers: Dict[str, Any],
    mock_say: Any,
    caplog: LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    """Test hello message handler."""
    setup_message_handlers(mock_app)
    mock_app.message.assert_any_call("hello")
    handler = mock_handlers["message"]["hello"].handler
    message = {"user": "U123"}
    handler(message=message, say=mock_say)
    mock_say.assert_called_once()
    call_args = mock_say.call_args[1]
    blocks = call_args["blocks"]
    assert len(blocks) == 1
    assert blocks[0]["accessory"]["action_id"] == "button_click"
    assert f"Hey there <@{message['user']}>!" == call_args["text"]


def test_handle_ai_message(
    mock_app: Any,
    mock_handlers: Dict[str, Any],
    mock_say: Any,
    caplog: LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    """Test AI message handler."""
    ai_pattern = re.compile(r"^ai\s+", re.IGNORECASE)

    mock_agent = mocker.MagicMock()
    mocker.patch(
        "slack_ai_agent.slack.handler.message_handlers.create_agent",
        return_value=mock_agent,
    )
    mock_response = AIMessage(content="Test response")
    mocker.patch(
        "slack_ai_agent.slack.handler.message_handlers.run_agent",
        return_value=[mock_response],
    )

    setup_message_handlers(mock_app)
    mock_app.message.assert_any_call(ai_pattern)
    handler = mock_handlers["message"][ai_pattern].handler
    message = {"text": "ai test message", "ts": "123.456"}
    handler(message=message, say=mock_say)
    mock_say.assert_called_once_with(text="Test response", thread_ts="123.456")


def test_handle_ai_message_empty(
    mock_app: Any,
    mock_handlers: Dict[str, Any],
    mock_say: Any,
    caplog: LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    """Test AI message handler with empty message."""
    mocker.patch(
        "slack_ai_agent.slack.handler.message_handlers.create_agent",
        return_value=mocker.MagicMock(),
    )

    ai_pattern = re.compile(r"^ai\s+", re.IGNORECASE)
    setup_message_handlers(mock_app)
    mock_app.message.assert_any_call(ai_pattern)
    handler = mock_handlers["message"][ai_pattern].handler
    message = {"text": "ai", "ts": "123.456"}
    handler(message=message, say=mock_say)
    mock_say.assert_called_once_with(
        text="Please provide a message for the AI agent to process.",
        thread_ts="123.456",
    )
