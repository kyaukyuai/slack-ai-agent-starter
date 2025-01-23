"""Test configuration module."""

from typing import Any
from typing import Dict

import pytest
from pytest_mock import MockerFixture
from slack_bolt import App


@pytest.fixture
def mock_handlers(mocker: MockerFixture) -> Dict[str, Any]:
    """Create mock handlers for testing."""
    return {
        "action": mocker.MagicMock(),
        "event": {
            "app_home_opened": mocker.MagicMock(),
            "app_mention": mocker.MagicMock(),
            "message": mocker.MagicMock(),
        },
        "message": {
            "hello": mocker.MagicMock(),
            "ai": mocker.MagicMock(),
        },
    }


@pytest.fixture
def mock_client(mocker: MockerFixture) -> Any:
    """Create a mock Slack client for testing."""
    client = mocker.MagicMock()
    client.conversations_replies.return_value = {"messages": []}
    client.views_publish.return_value = {"ok": True}
    return client


@pytest.fixture
def mock_app(
    mocker: MockerFixture, mock_handlers: Dict[str, Any], mock_client: Any
) -> App:
    """Create a mock Slack app instance for testing."""
    mocker.patch(
        "slack_bolt.App.client",
        new_callable=mocker.PropertyMock,
        return_value=mock_client,
    )

    app = App(
        token="xoxb-test-token",
        signing_secret="test-secret",
        token_verification_enabled=False,
    )

    # Mock the decorator methods
    def store_action_handler(action_id: str) -> Any:
        def decorator(func: Any) -> Any:
            mock_handlers["action"].handler = func
            mock_handlers["action"].action_id = action_id
            return func

        return decorator

    def store_event_handler(event_type: str) -> Any:
        def decorator(func: Any) -> Any:
            mock_handlers["event"][event_type].handler = func
            mock_handlers["event"][event_type].event_type = event_type
            return func

        return decorator

    def store_message_handler(pattern: str) -> Any:
        def decorator(func: Any) -> Any:
            mock_handlers["message"][pattern].handler = func
            mock_handlers["message"][pattern].pattern = pattern
            return func

        return decorator

    # Replace app decorators with mocks
    mocker.patch.object(app, "action", side_effect=store_action_handler)
    mocker.patch.object(app, "event", side_effect=store_event_handler)
    mocker.patch.object(app, "message", side_effect=store_message_handler)

    return app


@pytest.fixture
def mock_say(mocker: MockerFixture) -> Any:
    """Create a mock say function for testing."""
    return mocker.MagicMock()


@pytest.fixture
def mock_ack(mocker: MockerFixture) -> Any:
    """Create a mock ack function for testing."""
    return mocker.MagicMock()


@pytest.fixture
def mock_logger(mocker: MockerFixture) -> Any:
    """Create a mock logger for testing."""
    return mocker.MagicMock()
