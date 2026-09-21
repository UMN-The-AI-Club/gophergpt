import asyncio
import hashlib
import json
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
from autonomy.rag.vector_store import init_db
from autonomy.tools.gophergrades_api import fetch_search, fetch_prof


@asynccontextmanager
async def lifespan_function(app: FastAPI):
    init_store()
    dependencies.gopher_assistant = ChatAgent()

    try:
        init_db()
        print("PostgreSQL connected and schema ready.")
        csv_hash = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()
        try:
            with open(STAMP_PATH) as f:
                last_hash = f.read().strip()
        except FileNotFoundError:
            last_hash = ""

        if csv_hash != last_hash:
            print("CSV changed — re-indexing...")
            asyncio.create_task(run_indexing())
        else:
            print("Index is up to date — skipping re-index.")
            
    except Exception as e:
        print(f"WARNING: PostgreSQL connection failed: {e}")

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