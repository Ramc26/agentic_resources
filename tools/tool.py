import json
import logging
from typing import List, Dict

import requests
from duckduckgo_search import DDGS

def web_get(url: str) -> str:
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text


def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Perform a web search using the DuckDuckGo Search API.
    Returns a list of results: [{"title": str, "href": str}].
    """
    results: List[Dict[str, str]] = []
    try:
        with DDGS(timeout=10) as ddgs:
            search_results = list(ddgs.text(query, max_results=max_results))
            for item in search_results:
                results.append({
                    "title": item.get("title", ""),
                    "href": item.get("href", ""),
                })
    except Exception as e:
        logging.error(f"Error during web search for '{query}': {e}")

    if not results:
        logging.warning(f"No search results found for query: '{query}'")

    return results



def fetch_beeceptor_data() -> str:
    """
    Fetch plain text data from the Beeceptor test endpoint.

    Source: https://mp439f4be0115c967882.free.beeceptor.com/data
    """
    url = "https://mp439f4be0115c967882.free.beeceptor.com/data"
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text


