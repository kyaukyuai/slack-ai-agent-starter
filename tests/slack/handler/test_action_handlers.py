"""Test module for Slack action handlers."""

from typing import Any
from typing import Dict

from _pytest.logging import LogCaptureFixture
from pytest_mock import MockerFixture

from slack_ai_agent.slack.handler.action_handlers import setup_action_handlers


def test_handle_button_click(
    mock_app: Any,
    mock_handlers: Dict[str, Any],
    mock_ack: Any,
    mock_say: Any,
    caplog: LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    """Test button click handler.

    Args:
        mock_app: Mock Slack app instance
        mock_handlers: Mock handlers dictionary
        mock_ack: Mock ack function
        mock_say: Mock say function
        caplog: Pytest log capture fixture
        mocker: Pytest mocker fixture
    """
    # Setup action handlers
    setup_action_handlers(mock_app)

    # Verify handler was registered
    mock_app.action.assert_called_once_with("button_click")

    # Get the handler function
    handler = mock_handlers["action"].handler

    # Mock event body
    body = {"user": {"id": "U123"}}

    # Call handler
    handler(body=body, ack=mock_ack, say=mock_say)

    # Verify ack was called
    mock_ack.assert_called_once()

    # Verify say was called with correct message
    mock_say.assert_called_once_with("<@U123> clicked the button")
