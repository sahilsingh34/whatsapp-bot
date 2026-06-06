import logging
from typing import List, Dict
import asyncio
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

def _sync_ddg_search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """Synchronous DuckDuckGo search execution."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", ""),
                }
                for r in results
            ]
    except Exception as e:
        logger.error(f"Error executing synchronous DuckDuckGo search: {e}", exc_info=True)
        return []

async def web_search(query: str, max_results: int = 3) -> str:
    """
    Perform an asynchronous web search using DuckDuckGo.
    Returns a formatted string of the top results or an error message.
    """
    logger.info(f"🌐 Performing web search for query: '{query}'")
    results = await asyncio.to_thread(_sync_ddg_search, query, max_results)
    
    if not results:
        logger.warning(f"No search results returned for query: '{query}'")
        return "No search results found or search failed."
        
    formatted_results = []
    for i, r in enumerate(results, 1):
        formatted_results.append(
            f"Result [{i}]:\n"
            f"Title: {r['title']}\n"
            f"URL: {r['href']}\n"
            f"Snippet: {r['body']}\n"
        )
        
    return "\n---\n".join(formatted_results)
