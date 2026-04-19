"""
╔══════════════════════════════════════════════════════════════╗
║      FRIDAY — Web Search (modules/web_search.py)            ║
║  FREE STACK: DuckDuckGo (default, no key required)          ║
║  Optional: Tavily API (set HF_API_TOKEN in .env)            ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
from core.logger import get_logger
from config import SEARCH_PROVIDER, SEARCH_MAX_RESULTS

log = get_logger("WebSearch")


# ─────────────────────────────────────────────────────────────
# ▸ RESULT DATA CLASS
# ─────────────────────────────────────────────────────────────
class SearchResult:
    """Represents a single search result."""

    def __init__(self, title: str, url: str, body: str):
        self.title = title
        self.url   = url
        self.body  = body

    def __repr__(self):
        return f"SearchResult(title={self.title!r}, url={self.url!r})"

    def to_dict(self) -> dict:
        return {"title": self.title, "url": self.url, "body": self.body}

    def format(self) -> str:
        """Human-readable one-liner."""
        snippet = self.body[:200].replace("\n", " ")
        return f"[{self.title}]\n  {self.url}\n  {snippet}…"


# ─────────────────────────────────────────────────────────────
# ▸ DUCKDUCKGO BACKEND (no API key required)
# ─────────────────────────────────────────────────────────────
def _search_duckduckgo(query: str, max_results: int) -> list[SearchResult]:
    """
    Use the duckduckgo-search library to perform a text search.
    Install: pip install duckduckgo-search
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        log.error("duckduckgo-search not installed.  Run: pip install duckduckgo-search")
        return []

    results: list[SearchResult] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    body=r.get("body", ""),
                )
            )
    return results


# ─────────────────────────────────────────────────────────────
# ▸ TAVILY BACKEND (richer, AI-optimised results)
# ─────────────────────────────────────────────────────────────
def _search_tavily(query: str, max_results: int) -> list[SearchResult]:
    """
    Use the Tavily Search API (optional upgrade).
    Set TAVILY_API_KEY in .env to enable.
    Install: pip install tavily-python
    """
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if not tavily_key:
        log.error("TAVILY_API_KEY not set in .env — falling back to DuckDuckGo.")
        return _search_duckduckgo(query, max_results)

    try:
        from tavily import TavilyClient
    except ImportError:
        log.error("tavily-python not installed. Run: pip install tavily-python")
        return []

    client = TavilyClient(api_key=tavily_key)
    response = client.search(query=query, max_results=max_results)

    results: list[SearchResult] = []
    for r in response.get("results", []):
        results.append(
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                body=r.get("content", ""),
            )
        )
    return results


# ─────────────────────────────────────────────────────────────
# ▸ PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────
def search(query: str, max_results: int | None = None) -> list[SearchResult]:
    """
    Perform a web search using the configured provider.

    Args:
        query       : The search query string.
        max_results : Override the default result count.

    Returns:
        List of SearchResult objects.
    """
    n = max_results or SEARCH_MAX_RESULTS
    log.info(f"Searching [{SEARCH_PROVIDER}]: {query!r}  (max {n})")

    if SEARCH_PROVIDER == "tavily":
        results = _search_tavily(query, n)
    else:
        results = _search_duckduckgo(query, n)

    log.info(f"Got {len(results)} result(s).")
    return results


def search_and_summarise(query: str, max_results: int | None = None) -> str:
    """
    Search the web and return a clean, numbered text summary of results.
    Ready to be injected directly into an LLM prompt as context.

    Args:
        query : The search query.

    Returns:
        Formatted multi-line string with all results.
    """
    results = search(query, max_results)
    if not results:
        return f"No results found for: {query}"

    lines = [f"Web search results for: '{query}'\n{'─'*60}"]
    for i, r in enumerate(results, 1):
        lines.append(f"\n[{i}] {r.title}\n    URL : {r.url}\n    Info: {r.body[:300]}")

    return "\n".join(lines)
