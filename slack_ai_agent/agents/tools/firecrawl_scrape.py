import os
from typing import Dict

from firecrawl import FirecrawlApp
from langsmith import traceable


@traceable
def firecrawl_scrape(url: str) -> Dict:
    """Scrape a webpage using the Firecrawl API.

    Args:
        url (str): The URL of the webpage to scrape

    Returns:
        dict: Scraped webpage content in markdown format, containing:
            - content (str): The webpage content converted to markdown
            - metadata (dict): Additional metadata about the webpage
            - status (str): Status of the scraping request
            - url (str): The original URL that was scraped"""

    firecrawl_client = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
    return firecrawl_client.scrape_url(url, params={"formats": ["markdown"]})
