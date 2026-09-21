import os
from openai import AsyncOpenAI

# Indexing the full catalog sends ~31 batches back to back, which is enough to
# exhaust the embeddings tokens-per-minute quota and get a 429 partway through.
# The SDK honours the Retry-After on rate limit responses, so raising max_retries
# paces the run instead of failing it. The default of 2 is not enough at this size.
client = AsyncOpenAI(
    api_key=os.environ.get("OPENAI_KEY"),
    max_retries=8,
)

EMBEDDING_MODEL = "text-embedding-3-small"


async def embed_text(text: str) -> list[float]:
    """
    Embeds a single string and returns its vector representation.

    Used at query time — the user's question gets passed here before
    being sent to query_collection() in vector_store.py.
    The returned vector is what ChromaDB uses to find similar chunks.
    """
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )

    return response.data[0].embedding


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embeds a list of strings and returns a list of vectors.

    Used during indexing — instead of embedding one chunk at a time,
    we send a whole batch to the API in one call for efficiency.
    The order of returned vectors matches the order of the input texts.
    """
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )

    return [item.embedding for item in response.data]