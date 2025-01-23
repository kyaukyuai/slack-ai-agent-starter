"""Test module for Slack event handlers."""

from typing import Any
from typing import Dict

from _pytest.logging import LogCaptureFixture
from pytest_mock import MockerFixture

from slack_ai_agent.slack.handler.event_handlers import setup_event_handlers


def test_update_home_tab(
    mock_app: Any,
    mock_handlers: Dict[str, Any],
    mock_client: Any,
    mock_logger: Any,
    caplog: LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    """Test home tab update handler.

    Args:
        mock_app: Mock Slack app instance
        mock_handlers: Mock handlers dictionary
        mock_client: Mock Slack client
        mock_logger: Mock logger instance
        caplog: Pytest log capture fixture
        mocker: Pytest mocker fixture
    """
    # Setup event handlers
    setup_event_handlers(mock_app)

    # Verify handler was registered
    mock_app.event.assert_any_call("app_home_opened")

    # Get the handler function
    handler = mock_handlers["event"]["app_home_opened"].handler

    # Mock event data
    event = {"user": "U123"}

    # Call handler
    handler(client=mock_client, event=event, logger=mock_logger)

    # Verify views_publish was called
    mock_client.views_publish.assert_called_once()
    call_args = mock_client.views_publish.call_args[1]
    assert call_args["user_id"] == "U123"
    assert call_args["view"]["type"] == "home"


def test_handle_message_events(
    mock_app: Any,
    mock_handlers: Dict[str, Any],
    mock_logger: Any,
    caplog: LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    """Test general message event handler.

    Args:
        mock_app: Mock Slack app instance
        mock_handlers: Mock handlers dictionary
        mock_logger: Mock logger instance
        caplog: Pytest log capture fixture
        mocker: Pytest mocker fixture
    """
    # Setup event handlers
    setup_event_handlers(mock_app)

    # Verify handler was registered
    mock_app.event.assert_any_call("message")

    # Get the handler function
    handler = mock_handlers["event"]["message"].handler

    # Mock event body
    body = {"message": "test"}

    # Call handler
    handler(body=body, logger=mock_logger)

    # Verify message was logged
    mock_logger.info.assert_called_once_with(body)
