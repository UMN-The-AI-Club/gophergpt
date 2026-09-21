import logging
import os
import re

from ..rag.retriever import retrieve
from langchain.tools import tool

from dotenv import load_dotenv
from langchain_tavily import TavilySearch


logger = logging.getLogger(__name__)

load_dotenv()
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")
tavily = TavilySearch(max_results=5, topic="general", search_depth="advanced", include_domains=["umn.edu", "reddit.com"])

def code_extractor(code: str):
    """
    Pulls a UMN course code out of free text, normalised to match the
    source_url that csv_catalog.py writes (e.g. "CSCI3081W").

    The trailing letter matters: the catalog stores writing-intensive and
    honors courses with their suffix ("3081W", "1133H"), so the suffix has to be
    kept or the exact-match filter lands on a source_url that does not exist and
    silently returns nothing.

    Returns:
        the normalised code, or None if the text contains no course code.
    """
    extract = re.search(r'\b([A-Z]{2,6})\s*(\d{4}[A-Z]?)\b', code, re.IGNORECASE)

    if not extract:
        return None

    # upper() because the filter is an exact string match against the catalog
    return f"{extract.group(1)}{extract.group(2)}".upper()


def _format_tavily(payload) -> str:
    """
    Flattens a TavilySearch result into readable text.

    tavily.invoke() returns a dict, but course_search is declared -> str and every
    other branch returns text. Handing the raw dict to the agent also feeds it
    images, request_id and response_time, which is noise it then has to reason
    around. Keep the synthesised answer and the result snippets.
    """
    if isinstance(payload, str):
        return payload

    if not isinstance(payload, dict):
        return str(payload)

    parts = []

    if payload.get("answer"):
        parts.append(str(payload["answer"]))

    for result in (payload.get("results") or []):
        content = (result.get("content") or "").strip()
        if content:
            parts.append(f"{result.get('title', '')} ({result.get('url', '')})\n{content}")

    return "\n\n".join(parts) if parts else "No course information found."


async def _retrieve_chunks(query: str, top_k: int = 5, where: dict | None = None):
    """
    Calls retrieve() and returns the raw chunk dicts for a given query

    Args:
        query: the user's question (e.g., "What are the prerequisites for CSCI 1111?")
        top_k: number of chunks to retrieve from ChromaDB, defaults to 5
        where: optional metadata filter passed to ChromaDB, e.g. {"source_url": "catalog:CSCI1133"} for exact course lookups, None for semantic search

    Returns:
        list of dicts, each containing text, source_url, source_name, and distance
    """
    chunks, _ = await retrieve(question=query, top_k=top_k, where=where)
    return chunks


@tool
async def course_search(query: str) -> str:
    """
    Primary tool for UMN course questions. Use for course descriptions, prerequisites, and offered terms. 
    Searches the course catalog database first, falls back to web search if no relevant results are found.

    Args:
        query: the user's question (e.g., "What are the prerequisites for CSCI 1111?")

    Returns:
        string of course information from the vector database or web search.    
    """

    try:
        code = code_extractor(query)
        where = {"source_url": f"catalog:{code}"} if code else None
        top_k = 1 if where else 5
        chunks = await _retrieve_chunks(query=query, where=where, top_k=top_k)

        if not chunks and where is not None:
            # the exact-match filter is all-or-nothing: a course code the catalog
            # spells differently, or a false positive off ordinary prose, pins the
            # lookup to a source_url that does not exist and returns zero rows.
            # Drop the filter and let semantic search answer rather than giving up.
            logger.info(
                "course_search exact lookup %s missed — retrying %r as semantic search.",
                where, query,
            )
            where = None
            chunks = await _retrieve_chunks(query=query, where=None, top_k=5)

        if not chunks:
            # an empty umn_docs collection looks identical to a genuine miss from
            # the agent's side, so say which one this was
            logger.warning(
                "course_search found no chunks for %r (filter=%s) — check umn_docs is populated.",
                query, where,
            )
            return "No course information found."

        if where is None and all(chunk["distance"] > 0.7 for chunk in chunks):
            logger.info(
                "course_search falling back to Tavily for %r — best distance %.4f exceeds 0.7.",
                query, min(chunk["distance"] for chunk in chunks),
            )
            return _format_tavily(tavily.invoke(query))

        else:
            logger.info(
                "course_search served %d chunk(s) from umn_docs for %r (filter=%s).",
                len(chunks), query, where,
            )
            text = ""
            for chunk in chunks:
                text += chunk["text"]

        return text
    except Exception as e:
        logger.exception("course_search failed for %r.", query)
        return f"Course search failed: {str(e)}"