import os
import re

from ..rag.retriever import retrieve
from langchain.tools import tool

from dotenv import load_dotenv
from langchain_tavily import TavilySearch


load_dotenv()
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")
tavily = TavilySearch(max_results=5, topic="general", search_depth="advanced", include_domains=["umn.edu", "reddit.com"])

def code_extractor(code: str):
    extract = re.search(r'\b([A-Z]{2,6})\s*(\d{4})\b', code)

    if not extract:
        return None
    
    return f"{extract.group(1)}{extract.group(2)}"


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

        if not chunks:
            return "No course information found."

        if where is None and all(chunk["distance"] > 0.7 for chunk in chunks):
            return tavily.invoke(query)
        
        else:
            text = ""
            for chunk in chunks:
                text += chunk["text"]   

        return text
    except Exception as e:
        return f"Course search failed: {str(e)}"