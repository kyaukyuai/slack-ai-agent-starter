"""Configuration management functionality for the agent implementation."""

from typing import Optional

from langchain_core.runnables import RunnableConfig

from .types import UserConfig


def get_user_config(config: Optional[RunnableConfig] = None) -> UserConfig:
    """Get user configuration from RunnableConfig.

    Args:
        config (Optional[RunnableConfig]): Runtime configuration

    Returns:
        UserConfig: User configuration dictionary

    Raises:
        ValueError: If user ID is None in config
    """
    if config is None:
        return UserConfig(
            user_id="langgraph-studio-user",
            preferences=None,
        )

    config_dict = config.get("configurable", {})
    user_id = config_dict.get("user_id", "langgraph-studio-user")

    if user_id is None:
        raise ValueError("User ID needs to be provided in the configuration.")

    return UserConfig(
        user_id=user_id,
        preferences=config_dict.get("preferences"),
    )
