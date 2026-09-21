import json
import logging
import os
import re
import time

import httpx

from autonomy.rag.sources.csv_catalog import build_course_document

logger = logging.getLogger(__name__)

CATALOG_HOST = "https://umtc.catalog.prod.coursedog.com"
API_HOST = "https://app.coursedog.com"

# The catalog API rejects anonymous callers with 401 unless this header is present.
# It is what the public catalog page sends on every one of its own requests — see
# the api client it builds in its JS bundle. Origin is sent alongside it there, so
# send both rather than relying on only the part that happens to work today.
API_HEADERS = {
    "X-Requested-With": "coursedog-core",
    "Origin": CATALOG_HOST,
    "Referer": f"{CATALOG_HOST}/courses",
}

# used only if discovery fails; discovery is preferred because activeCatalog
# changes whenever UMN rolls the catalog year
FALLBACK_SCHOOL = "umn_umntc_peoplesoft"
FALLBACK_CATALOG_ID = "QEPaNgPjyzEkVlRYv42S"

PAGE_SIZE = 5000
REQUEST_TIMEOUT = 120.0


async def discover_catalog_config(client: httpx.AsyncClient) -> tuple[str, str]:
    """
    Reads the current school id and active catalog id off the public catalog page.

    These are embedded in the page's Nuxt payload. Discovering them beats
    hardcoding because activeCatalog changes when UMN rolls the catalog year — a
    stale hardcoded id would keep returning results for last year's catalog
    rather than failing, which is the worst kind of wrong.

    Returns:
        (school, catalog_id), falling back to known-good constants if the page
        layout changes.
    """
    try:
        response = await client.get(f"{CATALOG_HOST}/courses", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        payload = re.search(
            r'id="__NUXT_DATA__"[^>]*>(.*?)</script>', response.text, re.S
        )
        if not payload:
            raise ValueError("no __NUXT_DATA__ payload in the catalog page")

        entries = json.loads(payload.group(1))

        # the payload is a flat array of values plus an index map; find the map
        # holding these keys, then dereference each one
        index_map = next(
            entry for entry in entries
            if isinstance(entry, dict)
            and "activeCatalog" in entry
            and "school" in entry
        )
        school = entries[index_map["school"]]
        catalog_id = entries[index_map["activeCatalog"]]

        if not isinstance(school, str) or not isinstance(catalog_id, str):
            raise ValueError(f"unexpected types: school={school!r} catalog={catalog_id!r}")

        logger.info("Discovered Coursedog config: school=%s catalog=%s", school, catalog_id)
        return school, catalog_id

    except Exception as error:
        logger.warning(
            "Could not discover Coursedog config (%s) — falling back to school=%s catalog=%s. "
            "If course results look like the wrong catalog year, this is why.",
            error, FALLBACK_SCHOOL, FALLBACK_CATALOG_ID,
        )
        return FALLBACK_SCHOOL, FALLBACK_CATALOG_ID


async def fetch_raw_courses() -> list[dict]:
    """
    Pulls every course record from the Coursedog catalog API.

    Pages through /courses/search/$filters until the reported listLength is
    covered. Returns the raw API records; filtering and formatting happen in
    load_api_catalog() so the cache can store the unprocessed payload.

    Raises:
        httpx.HTTPError if the API cannot be reached or returns an error status.
    """
    async with httpx.AsyncClient(headers=API_HEADERS, timeout=REQUEST_TIMEOUT) as client:
        school, catalog_id = await discover_catalog_config(client)
        url = f"{API_HOST}/api/v1/cm/{school}/courses/search/$filters"

        courses: list[dict] = []
        skip = 0
        total = None

        while total is None or skip < total:
            response = await client.get(
                url, params={"catalogId": catalog_id, "limit": PAGE_SIZE, "skip": skip}
            )
            response.raise_for_status()
            body = response.json()

            if total is None:
                total = body.get("listLength", 0)
                logger.info("Coursedog reports %d courses in catalog %s.", total, catalog_id)

            batch = body.get("data") or []
            if not batch:
                # defend against a server that keeps reporting a listLength it
                # will not actually serve, rather than looping forever
                logger.warning(
                    "Coursedog returned an empty page at skip=%d (expected %d total) — stopping.",
                    skip, total,
                )
                break

            courses.extend(slim_course(course) for course in batch)
            skip += len(batch)
            logger.info("Fetched %d/%s courses.", len(courses), total)

        return courses


# the API returns ~90 fields per course; caching all of them costs ~141MB for
# 25k records, which then gets mounted into the container and re-read on every
# start. Keep only what to_documents() reads.
CACHED_FIELDS = (
    "code",
    "subjectCode",
    "courseNumber",
    "name",
    "longName",
    "description",
    "status",
    "courseTypicallyOffered",
)


def slim_course(course: dict) -> dict:
    """Projects a raw API record down to the fields the indexer actually uses."""
    slim = {field: course.get(field) for field in CACHED_FIELDS}
    # credits is nested; keep just the hours rather than the whole repeat policy
    slim["credits"] = {"creditHours": (course.get("credits") or {}).get("creditHours") or {}}
    return slim


def _credit_hours(course: dict) -> tuple:
    """Pulls (min, max) credit hours out of the nested credits object."""
    hours = ((course.get("credits") or {}).get("creditHours")) or {}
    minimum = hours.get("min", "")
    return minimum, hours.get("max", minimum)


def to_documents(raw_courses: list[dict]) -> list[dict]:
    """
    Turns raw Coursedog API records into indexable documents.

    Drops anything a student cannot act on: Inactive courses (roughly 40% of the
    catalog) and courses with no description, which would index as an empty stub.

    Returns:
        list of document dicts matching what load_csv_catalog() produces.
    """
    documents = []
    inactive = 0
    no_description = 0
    no_code = 0

    for course in raw_courses:
        if course.get("status") != "Active":
            inactive += 1
            continue

        description = (course.get("description") or "").strip()
        if not description:
            no_description += 1
            continue

        # `code` already arrives normalised, W/H suffix included ("CSCI3081W"),
        # which is exactly the shape course_search's exact-match filter needs
        code = (course.get("code") or "").strip()
        if not code:
            no_code += 1
            continue

        minimum, maximum = _credit_hours(course)

        documents.append(build_course_document(
            code=code,
            name=course.get("name") or course.get("longName") or "",
            description=description,
            min_credits=minimum,
            max_credits=maximum,
            typically_offered=course.get("courseTypicallyOffered") or "",
        ))

    logger.info(
        "Built %d course documents from %d API records "
        "(skipped %d inactive, %d without a description, %d without a code).",
        len(documents), len(raw_courses), inactive, no_description, no_code,
    )

    return documents


async def load_api_catalog(cache_path: str | None = None, max_age_hours: float = 24.0) -> list[dict]:
    """
    Returns catalog documents, fetching from Coursedog and caching the payload.

    A fresh cache avoids re-pulling ~25k records on every container restart. The
    cache stores the projected records (see CACHED_FIELDS), not the formatted
    text, so changing the chunk wording only needs a re-index, not a re-fetch.

    Args:
        cache_path: where to read/write the payload; None disables caching.
        max_age_hours: reuse the cache if it is younger than this.

    Returns:
        list of document dicts ready for index_source().
    """
    raw = _read_cache(cache_path, max_age_hours) if cache_path else None

    if raw is None:
        raw = await fetch_raw_courses()
        if cache_path:
            _write_cache(cache_path, raw)

    return to_documents(raw)


def _read_cache(path: str, max_age_hours: float) -> list[dict] | None:
    """Returns the cached payload if present and fresh, else None."""
    try:
        if not os.path.isfile(path):
            return None

        age_hours = (time.time() - os.path.getmtime(path)) / 3600
        if age_hours > max_age_hours:
            logger.info("Coursedog cache %s is %.1fh old (max %.1fh) — refetching.", path, age_hours, max_age_hours)
            return None

        with open(path, "r") as handle:
            raw = json.load(handle)

        logger.info("Using cached Coursedog payload %s (%.1fh old, %d records).", path, age_hours, len(raw))
        return raw

    except Exception:
        logger.warning("Could not read Coursedog cache %s — refetching.", path, exc_info=True)
        return None


def _write_cache(path: str, raw: list[dict]) -> None:
    """Writes the raw payload to the cache, never failing the caller."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # write-then-rename so a crash mid-write cannot leave a truncated cache
        # that later parses as valid-but-short
        temporary = f"{path}.tmp"
        with open(temporary, "w") as handle:
            json.dump(raw, handle)
        os.replace(temporary, path)
        logger.info("Cached %d Coursedog records to %s.", len(raw), path)
    except Exception:
        logger.warning("Could not write Coursedog cache %s.", path, exc_info=True)
