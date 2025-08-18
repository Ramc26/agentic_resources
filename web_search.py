import logging
from typing import List, Dict
from ddgs import DDGS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

if __name__ == '__main__':
    search_query = "who is Chiranjeevi?"
    search_results = web_search(search_query)
    
    print(f"Search results for: '{search_query}'\n")
    if search_results:
        for item in search_results:
            print(f"Title: {item['title']}")
            print(f"Link: {item['href']}\n")
    else:
        print("No results were returned.")