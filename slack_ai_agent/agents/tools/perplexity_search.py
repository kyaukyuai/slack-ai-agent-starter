import os

import requests  # type: ignore
from langsmith import traceable


@traceable
def perplexity_search(search_queries):
    """Search the web using the Perplexity API.

    Args:
        search_queries (List[str]): List of search query strings to process

    Returns:
        List[dict]: List of search responses from Perplexity API, one per query. Each response has format:
            {
                'query': str,                    # The original search query
                'follow_up_questions': None,
                'answer': None,
                'images': list,
                'results': [                     # List of search results
                    {
                        'title': str,            # Title of the search result
                        'url': str,              # URL of the result
                        'content': str,          # Summary/snippet of content
                        'score': float,          # Relevance score
                        'raw_content': str|None  # Full content or None for secondary citations
                    },
                    ...
                ]
            }
    """

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
    }

    search_docs = []
    for query in search_queries:
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "Search the web and provide factual information with sources.",
                },
                {"role": "user", "content": query},
            ],
        }

        response = requests.post(
            "https://api.perplexity.ai/chat/completions", headers=headers, json=payload
        )
        response.raise_for_status()  # Raise exception for bad status codes

        # Parse the response
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", ["https://perplexity.ai"])

        # Create results list for this query
        results = []

        # First citation gets the full content
        results.append(
            {
                "title": "Perplexity Search, Source 1",
                "url": citations[0],
                "content": content,
                "raw_content": content,
                "score": 1.0,  # Adding score to match Tavily format
            }
        )

        # Add additional citations without duplicating content
        for i, citation in enumerate(citations[1:], start=2):
            results.append(
                {
                    "title": f"Perplexity Search, Source {i}",
                    "url": citation,
                    "content": "See primary source for full content",
                    "raw_content": None,
                    "score": 0.5,  # Lower score for secondary sources
                }
            )

        # Format response to match Tavily structure
        search_docs.append(
            {
                "query": query,
                "follow_up_questions": None,
                "answer": None,
                "images": [],
                "results": results,
            }
        )

    return search_docs
