import asyncio
import hashlib
import json
import logging
import os
import webservice.dependencies as dependencies

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from webservice.routers.chat import router as chat_router
from webservice.routers.courses import router as course_router
from webservice.routers.research import router as research_router
from webservice.routers.profile import router as profile_router
from webservice.profile_store import init_store
from webservice.agent import ChatAgent
from autonomy.rag.indexer import run_indexing, CSV_PATH, STAMP_PATH
from autonomy.rag.vector_store import init_db, count_chunks
from autonomy.rag.sources.csv_catalog import CATALOG_SOURCE_NAME
from autonomy.tools.gophergrades_api import fetch_search, fetch_prof


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

def _csv_export_changed() -> bool:
    """
    CSV-mode staleness: re-index when the hand-dropped export's hash moved.

    Only meaningful when CATALOG_SOURCE=csv — in API mode (the default) the
    indexer pulls from Coursedog and the CSV, which may not even exist, says
    nothing about freshness.
    """
    if (os.getenv("CATALOG_SOURCE") or "api").lower() != "csv":
        return False
    try:
        csv_hash = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()
    except OSError:
        return False
    try:
        with open(STAMP_PATH) as f:
            last_hash = f.read().strip()
    except FileNotFoundError:
        last_hash = ""
    return csv_hash != last_hash


def _needs_catalog_indexing() -> bool:
    """
    Decides whether run_indexing() should fire, and says why.

    A plain total-count check is not enough. The embeddings table can be
    non-empty yet hold nothing course_search can use — leftovers from the
    retired ClassInfoScraper are stored under their scraped page URL, while
    course_search filters on source_url == "catalog:<CODE>". A store full of
    those looks healthy to a count check and permanently suppresses indexing
    of the real catalog.

    Set FORCE_REINDEX=1 to re-index regardless.

    Returns:
        True if the catalog should be indexed now.
    """
    if os.getenv("FORCE_REINDEX", "").lower() in ("1", "true", "yes"):
        logger.warning("FORCE_REINDEX set — re-indexing the catalog.")
        return True

    catalog = count_chunks(CATALOG_SOURCE_NAME)
    if catalog == 0:
        total = count_chunks()
        logger.warning(
            "embeddings table holds %d chunk(s) but none from %s — course_search's "
            "exact-code lookup cannot match any of them. Starting background indexer.",
            total, CATALOG_SOURCE_NAME,
        )
        return True

    if _csv_export_changed():
        logger.warning("Catalog CSV changed since the last index — re-indexing.")
        return True

    logger.info("Catalog already indexed (%d chunks) — skipping.", catalog)
    return False


def _log_indexing_result(task: asyncio.Task) -> None:
    """
    Done-callback for the background indexing task started during startup.

    asyncio.create_task() discards whatever the coroutine raises unless someone
    retrieves it, so an indexing crash left no trace at all — the app booted
    "successfully" with an empty umn_docs collection and every course_search
    call fell through to "No course information found." This reports the
    outcome either way, so a failed index is visible in the startup log.
    """
    if task.cancelled():
        logger.warning("Indexing task was cancelled before it finished — the store may be empty.")
        return

    error = task.exception()
    if error is not None:
        logger.error(
            "Indexing failed — the embeddings table was left as it was, which may be empty or stale.",
            exc_info=error,
        )
        return

    try:
        total = count_chunks()
        # count alone can be satisfied by unrelated leftovers, so report the
        # catalog chunks specifically — those are what course_search matches on
        catalog = count_chunks(CATALOG_SOURCE_NAME)
    except Exception:
        logger.exception("Indexing finished but the embeddings chunk count could not be read.")
        return

    if catalog == 0:
        logger.error(
            "Indexing finished but the store holds no catalog chunks (%d total) — "
            "course_search will find nothing.", total,
        )
    else:
        logger.info(
            "Indexing complete — the store holds %d catalog chunk(s) of %d total.",
            catalog, total,
        )


@asynccontextmanager
async def lifespan_function(app: FastAPI):
    init_store()
    dependencies.gopher_assistant = ChatAgent()

    try:
        init_db()
        logger.info("PostgreSQL connected and schema ready.")

        if await asyncio.to_thread(_needs_catalog_indexing):
            task = asyncio.create_task(run_indexing())
            task.add_done_callback(_log_indexing_result)
    except Exception:
        logger.exception(
            "PostgreSQL connection failed — course_search will find nothing until this is fixed."
        )

    yield


app = FastAPI(lifespan=lifespan_function)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(research_router)
app.include_router(chat_router)
app.include_router(course_router)
app.include_router(profile_router)


@app.get("/")
def root():
    return {"message": "The greatest openai wrapper ever made."}


def _search_prof_code(name):
    try:
        result = fetch_search(name)
        candidates = []

        def _extract_instructors(obj):
            if isinstance(obj, dict):
                for key in ("instructors", "professors", "instructor", "professor"):
                    val = obj.get(key)
                    if isinstance(val, list):
                        candidates.extend(val)
                for key in ("data", "results"):
                    if isinstance(obj.get(key), (dict, list)):
                        _extract_instructors(obj[key])
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        if any(k in item for k in ("instructor_id", "prof_id", "slug", "full_name")):
                            candidates.append(item)
                        else:
                            _extract_instructors(item)

        _extract_instructors(result)

        if candidates:
            first = candidates[0]
            code = (
                first.get("instructor_id")
                or first.get("prof_id")
                or first.get("id")
                or first.get("slug")
                or first.get("code")
            )
            display = (
                first.get("full_name")
                or first.get("name")
                or first.get("instructor_name")
                or name
            )
            if code:
                return str(code), display
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Prof search failed for %r", name)
    return None


@app.get("/debug/prof")
def debug_prof(name: str):
    search_raw = fetch_search(name)
    found = _search_prof_code(name)
    prof_raw = None
    if found:
        code, _ = found
        prof_raw = fetch_prof(code)
    return {"search": search_raw, "found": found, "prof": prof_raw}