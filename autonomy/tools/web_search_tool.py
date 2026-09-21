import re

from langchain.tools import tool
from langchain_tavily import TavilySearch

# Lazily built so TAVILY_API_KEY (set during ChatAgent init) is available.
_tavily = None


def _get_tavily():
    global _tavily
    if _tavily is None:
        _tavily = TavilySearch(
            max_results=5,
            topic="general",
            search_depth="advanced",
            include_domains=["umn.edu", "reddit.com"],
        )
    return _tavily


def _summarize(res, query: str) -> str:
    results = res.get("results") if isinstance(res, dict) else res
    if not results:
        return f'No web results for "{query}".'
    lines = [f'Web results for "{query}":']
    for r in results[:5]:
        title = (r.get("title") or "").strip()
        url = r.get("url") or ""
        snippet = re.sub(r"\s+", " ", (r.get("content") or "")).strip()[:200]
        lines.append(f"- {title} ({url})\n  {snippet}")
    return "\n".join(lines)


@tool
def tavily_search(query: str) -> str:
    """
    General UMN web search for questions the other tools don't cover
    (campus life, events, resources, policies). Returns the top results, each
    with its title, URL, and a short snippet.
    """
    try:
        return _summarize(_get_tavily().invoke({"query": query}), query)
    except Exception as e:
        return f"Web search failed: {e}"
