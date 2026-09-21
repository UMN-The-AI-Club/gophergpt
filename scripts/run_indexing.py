import asyncio
from autonomy.rag.indexer import run_indexing


# an async function from a regular script
asyncio.run(run_indexing())