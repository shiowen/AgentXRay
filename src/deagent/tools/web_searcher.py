# tools/web_searcher.py
# A simple, dependency-based static tool for performing web searches.
# This is a production-ready module intended for import by the agent system.

import logging
from ddgs import DDGS

#  logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def web_searcher(query: str) -> str:
    """
    Performs a web search using the DuckDuckGo search engine and returns a
    formatted summary of the top results.

    Args:
        query (str): The search query string.

    Returns:
        str: A formatted string containing the title, snippet, and URL of
             the top search results, or an error message if the search fails.
    """
    if not query or not isinstance(query, str) or not query.strip():
        return "Web Search Error: The search query cannot be empty."

    logger.info(f"Performing web search for: '{query}'")
    
    try:
        #  DDGS() 
        with DDGS() as ddgs:
            #  .text() 
            results = list(ddgs.text(query, max_results=5))

        if not results:
            return f"No web results found for the query: '{query}'"

        formatted_output = f"Web search results for '{query}':\n\n"
        for i, result in enumerate(results, 1):
            formatted_output += f"Result {i}:\n"
            formatted_output += f"  Title: {result.get('title', 'N/A')}\n"
            formatted_output += f"  Snippet: {result.get('body', 'N/A')}\n"
            formatted_output += f"  URL: {result.get('href', 'N/A')}\n\n"

        return formatted_output.strip()

    except Exception as e:
        error_message = f"Web Search Error: An unexpected error occurred. Details: {str(e)}"
        logger.error(error_message, exc_info=True)
        return error_message
