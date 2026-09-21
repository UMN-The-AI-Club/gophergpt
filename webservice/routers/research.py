from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import os
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

router = APIRouter()


class ResearchRequest(BaseModel):
    """Request model for research query endpoint."""
    query: str
    max_results: Optional[int] = 5


class ResearchResult(BaseModel):
    """Represents a single research result."""
    title: str
    url: str
    snippet: str


class ResearchResponse(BaseModel):
    """Response model for research query endpoint."""
    results: List[ResearchResult]
    source: str
    summary: Optional[str] = None


UMN_RESEARCH_HOST_KEYWORDS = (
    "umn.edu",
)


RESEARCH_PATH_HINTS = (
    "research",
    "urop",
    "reu",
    "lab",
    "faculty",
    "undergraduate-research",
    "opportunities",
)


EXCLUDED_URL_HINTS = (
    "indeed.com",
    "handshake.com",
    "jobs",
    "job",
    "internship",
    "internships",
    "course-search",
    "publiccoursesearchdetails",
)


def _is_umn_url(url: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    return any(keyword in host for keyword in UMN_RESEARCH_HOST_KEYWORDS)


def _looks_like_umn_research_result(title: str, url: str, snippet: str) -> bool:
    combined = f"{title} {url} {snippet}".lower()

    if not _is_umn_url(url):
        return False

    if any(hint in combined for hint in EXCLUDED_URL_HINTS):
        return False

    return any(hint in combined for hint in RESEARCH_PATH_HINTS)


def run_research_query(request: ResearchRequest) -> ResearchResponse:
    """
    Executes a research query using Tavily search and returns ranked results.

    Args:
        request: ResearchRequest containing the query string and max results

    Returns:
        a ResearchResponse with results, source, and optional summary
    """
    load_dotenv()
    logger.info("/research POST called; query=%s, max_results=%s", request.query, request.max_results)
    openai_key = os.getenv("OPENAI_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")

    if not (openai_key and tavily_key):
        sample = [
            ResearchResult(
                title="Sample UMN Result",
                url="https://umn.edu/sample-paper",
                snippet=(
                    "This is a canned sample result returned because OPENAI_KEY or "
                    "TAVILY_API_KEY was not found in the environment. Replace them in "
                    ".env to enable live search."
                ),
            )
        ]
        logger.info("Missing API keys; returning mock response")
        return ResearchResponse(results=sample, source="mock")

    try:
        from autonomy.llm.openai_llm import OpenAILLM
        from langchain_tavily import TavilySearch
        from autonomy.llm.factory import get_llm

        llm = get_llm().get_model()
        search = TavilySearch(
            max_results=str(request.max_results),
            topic="general",
            search_depth="advanced",
            include_domains=["umn.edu", "ugresearch.umn.edu", "cse.umn.edu", "med.umn.edu", "twin-cities.umn.edu", "d.umn.edu"],
        )

        raw = search.run(request.query)

        results: List[ResearchResult] = []

        def clean_text(s: Optional[str]) -> str:
            """
            Cleans and normalizes a text string.

            Args:
                s: the string to clean

            Returns:
                a cleaned string with extra whitespace and brackets removed
            """
            if not s:
                return ""
            text = " ".join(str(s).split()).strip()
            text = text.replace("{", "").replace("}", "").replace("[", "").replace("]", "")
            return text

        def flatten_raw(obj):
            """
            Recursively flattens nested dicts and lists from Tavily response.

            Args:
                obj: the object to flatten, can be a dict, list, or other type

            Returns:
                a flat list of items
            """
            items = []
            if isinstance(obj, dict):
                if "results" in obj and isinstance(obj["results"], list) and obj["results"]:
                    for x in obj["results"]:
                        items.extend(flatten_raw(x))
                else:
                    items.append(obj)
            elif isinstance(obj, list):
                for x in obj:
                    items.extend(flatten_raw(x))
            else:
                items.append(obj)
            return items

        normalized_items = flatten_raw(raw)

        if len(normalized_items) == 1 and isinstance(normalized_items[0], dict):
            wrapper = normalized_items[0]
            if "results" in wrapper and isinstance(wrapper["results"], list) and wrapper["results"]:
                normalized_items = flatten_raw(wrapper["results"])

        for item in normalized_items:
            if isinstance(item, dict):
                title = clean_text(item.get("title") or item.get("metadata", {}).get("title", "") or item.get("name", ""))
                url = clean_text(item.get("url") or item.get("metadata", {}).get("source", "") or item.get("source", ""))
                snippet = clean_text(
                    item.get("snippet")
                    or item.get("content")
                    or item.get("raw_content")
                    or item.get("summary")
                    or item.get("text")
                    or item.get("excerpt")
                )
            else:
                title = "Result"
                url = ""
                snippet = clean_text(str(item))

            if _looks_like_umn_research_result(title, url, snippet):
                results.append(
                    ResearchResult(
                        title=title or "Untitled",
                        url=url or "",
                        snippet=snippet[:500],
                    )
                )

        if not results:
            logger.info("No filtered UMN research results found; returning empty result set")

        logger.info("Tavily search returned %d results", len(results))

        summary = "\n\n".join([r.snippet for r in results[:5]]) if results else None
        return ResearchResponse(results=results, source="tavily", summary=summary)

    except Exception as e:
        logger.exception("Error during research endpoint")
        fallback = [
            ResearchResult(
                title="Fallback Result (error)",
                url="",
                snippet=f"Search failed: {str(e)}",
            )
        ]
        return ResearchResponse(results=fallback, source="fallback")


@router.post("/research", response_model=ResearchResponse)
def research_endpoint(request: ResearchRequest):
    """
    Handles POST requests to the research endpoint.

    Args:
        request: ResearchRequest containing the query string and max results

    Returns:
        a ResearchResponse with results, source, and optional summary
    """
    return run_research_query(request)


@router.get("/research")
def research_info():
    """
    Returns usage information for the research endpoint.

    Returns:
        a dict with usage instructions and an example request body
    """
    example = {"query": "climate change adaptation", "max_results": 3}
    return {
        "message": "POST to this endpoint with JSON body {query, max_results}.",
        "example_body": example,
        "note": "If OPENAI_KEY or TAVILY_API_KEY are not set this endpoint returns a mock result for testing.",
    }