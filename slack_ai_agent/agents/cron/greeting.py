"""Module for setting up cron jobs for greeting messages."""

import asyncio
import logging
import os
from typing import Optional

from langgraph_sdk import get_client


logger = logging.getLogger(__name__)


class GreetingCronManager:
    """Manager class for handling greeting cron jobs."""

    def __init__(
        self, langgraph_url: Optional[str] = None, langgraph_token: Optional[str] = None
    ) -> None:
        """Initialize the greeting cron manager.

        Args:
            langgraph_url: URL for the LangGraph service
            langgraph_token: Authentication token for LangGraph
        """
        self.langgraph_url = langgraph_url or os.getenv("LANGGRAPH_URL")
        self.langgraph_token = langgraph_token or os.getenv("LANGGRAPH_TOKEN")
        self.assistant_id = "agent"

    def _get_client(self):
        """Create and return a LangGraph client.

        Returns:
            LangGraph client instance
        """
        if not self.langgraph_url or not self.langgraph_token:
            raise ValueError("LangGraph URL and token must be provided")

        return get_client(
            url=self.langgraph_url,
            headers={"Authorization": f"Bearer {self.langgraph_token}"},
        )

    async def setup_greeting_cron(self) -> None:
        """Set up a cron job for sending greeting messages."""
        try:
            client = self._get_client()
            await client.crons.create(
                self.assistant_id,
                schedule="27 15 * * *",
                input={"messages": [{"role": "user", "content": "What time is it?"}]},
            )
            logger.info("Successfully set up greeting cron job")
        except Exception as e:
            logger.error(f"Failed to set up greeting cron job: {e}")
            raise


async def main() -> None:
    """Main function to set up greeting cron jobs."""
    cron_manager = GreetingCronManager()
    await cron_manager.setup_greeting_cron()


if __name__ == "__main__":
    asyncio.run(main())
