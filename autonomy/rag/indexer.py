import hashlib
import json
import logging
import os
from pathlib import Path

from autonomy.rag.chunker import chunk_text
from autonomy.rag.embedder import embed_batch
from autonomy.rag.vector_store import upsert_chunks
from autonomy.rag.sources.classinfo import ClassInfoScraper
from autonomy.tools.gophergrades_api import fetch_dept
from autonomy.rag.sources.csv_catalog import load_csv_catalog
from autonomy.rag.sources.coursedog_api import load_api_catalog


logger = logging.getLogger(__name__)

# anchored to this file rather than the cwd — the indexer runs both from the
# repo root (scripts/run_indexing.py) and from /usr/src/app inside the container
DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLE_CATALOG = DATA_DIR / "sample_courses.csv"

# raw Coursedog payload, cached so a restart does not re-pull ~25k records.
# Lives in DATA_DIR, which docker-compose mounts from the host.
API_CACHE_PATH = DATA_DIR / "courses_api.json"


def resolve_catalog_path() -> Path:
    """
    Picks which catalog CSV to index and says out loud which one it chose.

    The full Coursedog export (courses.csv) is gitignored, so it is present only
    on machines where someone downloaded it. Rather than dying with a bare
    FileNotFoundError when it is absent, fall back to the committed sample so the
    pipeline still runs end-to-end — but log loudly, because a sample-sized
    index means most course questions will miss.

    Set CATALOG_CSV_PATH to point at a catalog somewhere else.

    Returns:
        Path to the CSV that should be indexed.
    """
    catalog = Path(os.getenv("CATALOG_CSV_PATH", DATA_DIR / "courses.csv"))

    if catalog.is_file():
        logger.info("Indexing full course catalog from %s", catalog)
        return catalog

    if SAMPLE_CATALOG.is_file():
        logger.warning(
            "Course catalog %s not found — falling back to the sample at %s. "
            "Most course questions will miss until the full Coursedog export is in place.",
            catalog, SAMPLE_CATALOG,
        )
        return SAMPLE_CATALOG

    raise FileNotFoundError(
        f"No catalog CSV to index: neither {catalog} nor the sample fallback "
        f"{SAMPLE_CATALOG} exists. Export the catalog from "
        f"https://umtc.catalog.prod.coursedog.com/courses to {catalog}."
    )

CSV_PATH = str(DATA_DIR / "courses.csv")
STAMP_PATH = "/app/data/.last_indexed"

# unused
def get_urls_from_gophergrades(dept: str) -> list[str]:
    """
    Fetches course page URLs from the GopherGrades API for a given department.

    Called by run_indexing() to dynamically build the list of pages to scrape,
    rather than hardcoding URLs manually. Returns the onestop URL for each
    course in the department, which is what classinfo.py will scrape.
    """

    data = fetch_dept(dept)
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

    logger.info("Indexed %d chunks.", len(all_chunks))


async def load_catalog_documents() -> list[dict]:
    """
    Returns catalog documents from the live Coursedog API, or the CSV as a fallback.

    The API is the default because it stays current on its own — a hand-exported
    CSV is a snapshot that silently rots and only exists on whoever downloaded it.
    The CSV path remains for offline development and for the case where UMN
    changes the API out from under us.

    Set CATALOG_SOURCE=csv to skip the API entirely.

    Returns:
        list of document dicts ready for index_source().
    """
    # `or` rather than a getenv default: docker-compose passes these through as
    # empty strings when they are unset on the host, which a default would not catch
    source = (os.getenv("CATALOG_SOURCE") or "api").lower()

    if source == "api":
        try:
            documents = await load_api_catalog(
                cache_path=str(API_CACHE_PATH),
                max_age_hours=float(os.getenv("CATALOG_MAX_AGE_HOURS") or 24),
            )
            if documents:
                return documents
            logger.warning("Coursedog API returned no usable courses — falling back to CSV.")
        except Exception:
            logger.warning(
                "Coursedog API fetch failed — falling back to the CSV catalog.", exc_info=True
            )

    catalog = resolve_catalog_path()
    documents = load_csv_catalog(str(catalog))

    if not documents:
        raise ValueError(
            f"{catalog} produced no indexable rows — every row had an empty "
            f"'Course description'. Check the export is complete."
        )

    logger.info("Loaded %d course documents from %s", len(documents), catalog)
    return documents


async def run_indexing() -> None:
    """
    Orchestrates the full indexing pipeline for all UMN sources.

    Called by scripts/run_indexing.py to trigger a full re-index offline, and by
    the startup hook in webservice/app.py when the catalog is not yet indexed.
    Loads course documents, then passes them through index_source() to chunk,
    embed, and store in Postgres (pgvector).
    """

    documents = await load_catalog_documents()

    await index_source(documents=documents)

    logger.info("Indexing complete.")

    # Staleness stamp: record the CSV export's hash so csv-mode reboots can skip
    # re-indexing an unchanged file. Guarded — in API mode the CSV (and, outside
    # the container, /app/data) may not exist, and that must not fail the run.
    try:
        csv_hash = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()
        with open(STAMP_PATH, "w") as f:
            f.write(str(csv_hash))
    except OSError:
        pass
