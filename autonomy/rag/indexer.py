import hashlib
import json

from autonomy.rag.chunker import chunk_text
from autonomy.rag.embedder import embed_batch
from autonomy.rag.vector_store import upsert_chunks
from autonomy.rag.sources.classinfo import ClassInfoScraper
from autonomy.tools.gophergrades_api import gophergrades_dept
from autonomy.rag.sources.csv_catalog import load_csv_catalog

CSV_PATH = "autonomy/rag/data/courses.csv"
STAMP_PATH = "/app/data/.last_indexed"

# unused
def get_urls_from_gophergrades(dept: str) -> list[str]:
    """
    Fetches course page URLs from the GopherGrades API for a given department.

    Called by run_indexing() to dynamically build the list of pages to scrape,
    rather than hardcoding URLs manually. Returns the onestop URL for each
    course in the department, which is what classinfo.py will scrape.
    """

    raw = gophergrades_dept.invoke(dept)
    data = json.loads(raw)
    return [course["onestop"] for course in data["data"]["distributions"] if course["onestop"] is not None]


async def index_source(documents: list[dict]) -> None:
    """
    Runs the chunk → embed → store pipeline for one source's documents.

    Called by run_indexing() once per source. Each document dict coming in
    will have text, source_url, source_name, and scraped_at. After chunking,
    the source metadata needs to be added back onto each chunk before storing,
    since chunk_text() only returns text and chunk_index.
    """
    all_chunks = []

    for document in documents:
        chunks = chunk_text(document["text"])

        # prints which course is being indexed, comment out when unneeded
        # print(f"Indexing: {document['source_url']}")

        # if want text, instead of using course
        # print(f"Indexing: {document['source_url']}, {document["text"]}")

        for chunk in chunks:
            chunk["source_url"] = document["source_url"]
            chunk["source_name"] = document["source_name"]
            chunk["scraped_at"] = document["scraped_at"]
            all_chunks.append(chunk)

    BATCH_SIZE = 500
    all_embeddings = []
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i:i + BATCH_SIZE]
        batch_embeddings = await embed_batch([c["text"] for c in batch])
        all_embeddings.extend(batch_embeddings)

    UPSERT_BATCH_SIZE = 500
    for i in range(0, len(all_chunks), UPSERT_BATCH_SIZE):
        upsert_chunks(
            chunks=all_chunks[i:i + UPSERT_BATCH_SIZE],
            embeddings=all_embeddings[i:i + UPSERT_BATCH_SIZE]
        )

    print(f"Indexed {len(all_chunks)} chunks.")


async def run_indexing() -> None:
    """
    Orchestrates the full indexing pipeline for all UMN sources.

    Called by scripts/run_indexing.py to trigger a full re-index offline.
    Loads course documents from the Coursedog CSV catalog, then passes them
    through index_source() to chunk, embed, and store in ChromaDB.
    """

    # switch between test sample and actual dataset
    # documents = load_csv_catalog("autonomy/rag/data/sample_courses.csv")
    documents = load_csv_catalog("autonomy/rag/data/courses.csv")

    await index_source(documents=documents)

    print("Indexing complete.")

    # Staleness Check

    # write CSV's modified time to stamp file
    csv_hash = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()
    with open(STAMP_PATH, "w") as f:
        f.write(str(csv_hash))

