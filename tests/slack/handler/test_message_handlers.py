"""Test module for Slack message handlers."""

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
    """Test hello message handler.

    Args:
        mock_app: Mock Slack app instance
        mock_handlers: Mock handlers dictionary
        mock_say: Mock say function
        caplog: Pytest log capture fixture
        mocker: Pytest mocker fixture
    """
    # Setup message handlers
    setup_message_handlers(mock_app)

    # Verify handler was registered
    mock_app.message.assert_any_call("hello")

    # Get the handler function
    handler = mock_handlers["message"]["hello"].handler

    # Mock message data
    message = {"user": "U123"}

    # Call handler
    handler(message=message, say=mock_say)

    # Verify say was called with correct blocks and text
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
    """Test AI message handler.

    Args:
        mock_app: Mock Slack app instance
        mock_handlers: Mock handlers dictionary
        mock_say: Mock say function
        caplog: Pytest log capture fixture
        mocker: Pytest mocker fixture
    """
    # Mock AI agent
    mock_agent = mocker.MagicMock()
    mocker.patch(
        "slack_ai_agent.slack.handler.message_handlers.create_agent",
        return_value=mock_agent,
    )

    # Mock agent response
    mock_response = AIMessage(content="Test response")
    mocker.patch(
        "slack_ai_agent.slack.handler.message_handlers.run_agent",
        return_value=[mock_response],
    )

    # Setup message handlers
    setup_message_handlers(mock_app)

    # Verify handler was registered
    mock_app.message.assert_any_call("ai")

    # Get the handler function
    handler = mock_handlers["message"]["ai"].handler

    # Mock message data
    message = {"text": "ai test message"}

    # Call handler
    handler(message=message, say=mock_say)

    # Verify say was called with correct response
    mock_say.assert_called_once_with("Test response")


def test_handle_ai_message_empty(
    mock_app: Any,
    mock_handlers: Dict[str, Any],
    mock_say: Any,
    caplog: LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    """Test AI message handler with empty message.

    Args:
        mock_app: Mock Slack app instance
        mock_handlers: Mock handlers dictionary
        mock_say: Mock say function
        caplog: Pytest log capture fixture
        mocker: Pytest mocker fixture
    """
    # Mock AI agent
    mocker.patch(
        "slack_ai_agent.slack.handler.message_handlers.create_agent",
        return_value=mocker.MagicMock(),
    )

    # Setup message handlers
    setup_message_handlers(mock_app)

    # Verify handler was registered
    mock_app.message.assert_any_call("ai")

    # Get the handler function
    handler = mock_handlers["message"]["ai"].handler

    # Mock message data with empty AI command
    message = {"text": "ai"}

    # Call handler
    handler(message=message, say=mock_say)

    # Verify error message was sent
    mock_say.assert_called_once_with(
        "Please provide a message for the AI agent to process."
    )
