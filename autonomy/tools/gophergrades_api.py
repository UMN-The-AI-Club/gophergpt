import os
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import httpx
import redis as redis_client

from langchain.tools import tool


_CACHE_TTL = 60 * 60 * 24 * 30  # 30 days — grade data changes once a semester


def _get_redis():
    return redis_client.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True,
    )


def _cache_get(url: str):
    # Redis being down must never fail the request — treat it as a miss.
    try:
        cached = _get_redis().get(url)
    except Exception:
        return None
    if cached:
        print(f"[CACHE HIT] {url}")
        return json.loads(cached)
    return None


def _cache_set(url: str, data, ttl: int = _CACHE_TTL) -> None:
    try:
        _get_redis().setex(url, ttl, json.dumps(data))
    except Exception:
        pass


def _get_json(url: str, timeout: int = 12) -> dict:
    """Sync variant — safe from the sync /umn routes and debug endpoints."""
    cached = _cache_get(url)
    if cached is not None:
        return cached
    req = Request(url, headers={"User-Agent": "gophergpt/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _cache_set(url, data)
            return data
    except HTTPError as e:
        return {"success": False, "error": f"HTTPError {e.code}: {e.reason}", "url": url}
    except URLError as e:
        return {"success": False, "error": f"URLError: {e.reason}", "url": url}
    except Exception as e:
        return {"success": False, "error": f"Unknown error: {str(e)}", "url": url}


async def _get_json_async(url: str, timeout: int = 12) -> dict:
    """Async variant — used by the agent tools and async chat card paths."""
    cached = _cache_get(url)
    if cached is not None:
        return cached
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"User-Agent": "gophergpt/1.0"}, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            print(f"[CACHE MISS] {url}")
            _cache_set(url, data)
            return data
    except httpx.HTTPStatusError as e:
        return {"success": False, "error": f"HTTPError {e.response.status_code}", "url": url}
    except Exception as e:
        return {"success": False, "error": str(e), "url": url}


def _base_api() -> str:
    # Use deployed umn.lol by default, override in .env for local dev:
    # GOPHERGRADES_API_BASE=http://localhost:3000/api
    return os.getenv("GOPHERGRADES_API_BASE", "https://umn.lol/api").rstrip("/")


# ─── grade helpers ──────────────────────────────────────────────────────────

_GRADE_POINTS = {
    "A": 4.0, "A-": 3.667, "B+": 3.333, "B": 3.0, "B-": 2.667,
    "C+": 2.333, "C": 2.0, "C-": 1.667, "D+": 1.333, "D": 1.0, "F": 0.0,
}


def _grade_stats(grades: dict):
    """Return (ab_rate_pct, avg_gpa) from a grade-count dict, ignoring W/S/N/P."""
    if not isinstance(grades, dict):
        return None, None
    letters = {k: v for k, v in grades.items() if k in _GRADE_POINTS}
    total = sum(letters.values())
    if not total:
        return None, None
    ab = sum(v for k, v in letters.items() if k[0] in ("A", "B"))
    gpa = sum(_GRADE_POINTS[k] * v for k, v in letters.items()) / total
    return round(100 * ab / total), round(gpa, 2)


def _fmt_stats(grades: dict) -> str:
    ab, gpa = _grade_stats(grades)
    if ab is None:
        return "no grade data"
    return f"A/B {ab}%, avg GPA {gpa}"


# ─── raw fetchers (FULL data — used by the cards and /umn routes) ────────────

def fetch_search(query: str) -> dict:
    """Full GopherGrades search result. Not model-facing."""
    return _get_json(f"{_base_api()}/search?{urlencode({'q': query})}")


def fetch_class(class_code: str) -> dict:
    """Full class data (grades, SRT, per-prof distributions). Not model-facing."""
    normalized = class_code.replace(" ", "").upper()
    return _get_json(f"{_base_api()}/class/{normalized}")


def fetch_prof(prof_code: str) -> dict:
    """Full professor data. Not model-facing."""
    return _get_json(f"{_base_api()}/prof/{prof_code}")


def fetch_dept(dept_code: str) -> dict:
    """Full department data (large). Not model-facing."""
    return _get_json(f"{_base_api()}/dept/{dept_code.upper()}")


async def fetch_search_async(query: str) -> dict:
    """Async twin of fetch_search — use from async endpoints and tools."""
    return await _get_json_async(f"{_base_api()}/search?{urlencode({'q': query})}")


async def fetch_class_async(class_code: str) -> dict:
    """Async twin of fetch_class."""
    normalized = class_code.replace(" ", "").upper()
    return await _get_json_async(f"{_base_api()}/class/{normalized}")


async def fetch_prof_async(prof_code: str) -> dict:
    """Async twin of fetch_prof."""
    return await _get_json_async(f"{_base_api()}/prof/{prof_code}")


async def fetch_dept_async(dept_code: str) -> dict:
    """Async twin of fetch_dept."""
    return await _get_json_async(f"{_base_api()}/dept/{dept_code.upper()}")


# ─── summarizers (COMPACT text — what the agent actually reads) ──────────────

def _summarize_search(data: dict, query: str) -> str:
    if not data or not data.get("success"):
        return f'No results for "{query}".'
    d = data.get("data", {}) or {}
    out = [f'Search results for "{query}":']

    classes = d.get("classes") or []
    if classes:
        out.append("Classes:")
        for c in classes[:5]:
            out.append(f"- {c.get('class_name','?')} (id {c.get('id')}) — {c.get('class_desc','')}")

    profs = d.get("professors") or []
    if profs:
        out.append("Professors:")
        for p in profs[:5]:
            rmp = p.get("RMP_score")
            out.append(f"- {p.get('name','?')} (id {p.get('id')}{', RMP ' + str(rmp) if rmp else ''})")

    depts = d.get("departments") or []
    if depts:
        out.append("Departments:")
        for dep in depts[:5]:
            out.append(f"- {dep.get('dept_abbr') or dep.get('code','?')}: {dep.get('dept_name') or dep.get('name','')}")

    if len(out) == 1:
        return f'No matching classes, professors, or departments for "{query}".'
    return "\n".join(out)


def _summarize_class(data: dict) -> str:
    if not data or not data.get("data"):
        return "No grade data found for that course."
    d = data["data"]
    header = (f"{d.get('dept_abbr','')} {d.get('course_num','')} — {d.get('class_desc','')} "
              f"({d.get('total_students','?')} students; {_fmt_stats(d.get('total_grades', {}))})")
    lines = [header]

    # One line per distinct instructor — no per-term breakdown
    seen = {}
    for dist in d.get("distributions", []) or []:
        name = dist.get("professor_name")
        if not name or name in seen:
            continue
        rmp = dist.get("professor_RMP_score")
        rmp_s = f"RMP {rmp}" if rmp else "no RMP"
        seen[name] = f"- {name} ({rmp_s}; {_fmt_stats(dist.get('grades', {}))})"
    if seen:
        lines.append("Instructors:")
        lines.extend(list(seen.values())[:6])
    return "\n".join(lines)


def _summarize_prof(data: dict) -> str:
    if not data or not data.get("data"):
        return "No professor found for that code."
    d = data["data"]
    rmp = d.get("RMP_score")
    diff = d.get("RMP_diff")
    head = d.get("name", "This professor")
    bits = []
    if rmp:
        bits.append(f"RMP {rmp}")
    if diff:
        bits.append(f"difficulty {diff}")
    lines = [f"{head}" + (f" — {', '.join(bits)}" if bits else "")]

    # Aggregate grades across all their distributions for an overall tendency
    agg = {}
    courses = []
    for dist in d.get("distributions", []) or []:
        for g, n in (dist.get("grades") or {}).items():
            agg[g] = agg.get(g, 0) + n
        cn = dist.get("course_num")
        if cn and cn not in courses:
            courses.append(cn)
    if agg:
        lines.append(f"Overall grade tendency: {_fmt_stats(agg)}")
    if courses:
        lines.append("Courses taught: " + ", ".join(courses[:12]))
    return "\n".join(lines)


def _summarize_dept(data: dict) -> str:
    if not data or not data.get("data"):
        return "No department found for that code."
    d = data["data"]
    dists = d.get("distributions", []) or []
    lines = [f"{d.get('dept_abbr','')} — {d.get('dept_name','')} ({len(dists)} courses on record)."]
    # Show the largest courses by enrollment as highlights
    top = sorted(dists, key=lambda c: c.get("total_students", 0) or 0, reverse=True)[:8]
    if top:
        lines.append("Highest-enrollment courses:")
        for c in top:
            code = f"{c.get('dept_abbr','')} {c.get('course_num','')}".strip()
            lines.append(f"- {code} — {c.get('class_desc','')} ({_fmt_stats(c.get('total_grades', {}))})")
    lines.append("(For a full department breakdown, direct the user to the Department Explorer tab.)")
    return "\n".join(lines)


# ─── model-facing tools (return COMPACT summaries) ──────────────────────────

@tool
async def gophergrades_search(query: str) -> str:
    """
    Search UMN classes/instructors/departments using GopherGrades.
    Input: a free-text query (e.g., "CSCI 1933", "data structures", "Kauffman").
    Returns a short list of matching classes and professors WITH their IDs
    (use a professor's id with gophergrades_prof).
    """
    return _summarize_search(await fetch_search_async(query), query)


@tool
async def gophergrades_class(class_code: str) -> str:
    """
    Grade distributions + instructor ratings for a course.
    Input: course code like "CSCI1933" or "CSCI 1933".
    Returns a concise summary: overall A/B rate & average GPA, plus the top
    instructors with their ratings.
    """
    return _summarize_class(await fetch_class_async(class_code))


@tool
async def gophergrades_prof(prof_code: str) -> str:
    """
    Professor profile from GopherGrades.
    Input: the professor's id/code from a gophergrades_search result (not the name).
    Returns their rating, difficulty, courses taught, and overall grade tendency.
    """
    return _summarize_prof(await fetch_prof_async(prof_code))


@tool
async def gophergrades_dept(dept_code: str) -> str:
    """
    Department overview from GopherGrades.
    Input: dept code like "CSCI".
    Returns the department name, course count, and highest-enrollment courses only.
    """
    return _summarize_dept(await fetch_dept_async(dept_code))
