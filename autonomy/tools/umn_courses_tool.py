import os
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import httpx
import redis as redis_client

from langchain.tools import tool


_CACHE_TTL = 60 * 60 * 6  # 6 hours — section availability changes during registration


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
    """Sync variant — safe from the sync /umn routes."""
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
    """Async variant — used by the agent tool and async chat card paths."""
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


def _parse_time(t) -> int | None:
    if t is None:
        return None
    s = str(t).strip()
    if not s:
        return None
    if ":" in s:
        parts = s.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours * 60 + minutes
    val = int(s)
    if val == 12:
        return 12 * 60
    if val < 12:
        return (val + 12) * 60
    return val * 60


def resolve_sterm(term_str: str) -> str:
    term_norm = term_str.lower().strip()
    term_lst = term_norm.split()
    season_map = {"spring": 3, "summer": 5, "fall": 9}
    digit = season_map.get(term_lst[0])

    if digit is None:
        raise ValueError(f"Unknown season '{term_lst[0]}'. Valid options: spring, summer, fall")

    year = int(term_lst[1])
    return str((year - 1900) * 10 + digit)


def _sections_url(subject: str, catalog_number: str, term: str) -> str:
    sterm = resolve_sterm(term)
    return f"https://courses.umn.edu/campuses/UMNTC/terms/{sterm}/courses.json?q=catalog_number={catalog_number},subject_id={subject.upper()}"


def _parse_sections(data) -> list:
    if isinstance(data, dict) and data.get("success") is False:
        return []

    results = []
    for course in data.get("courses", []):
        credits = course.get("credits_maximum")
        for section in course.get("sections", []):
            if section.get("status") == "T":
                continue

            instructors = []
            for inst in section.get("instructors", []):
                if inst.get("role") == "PI":
                    instructors.append(inst.get("name"))

            meeting_patterns = []
            for mp in section.get("meeting_patterns", []):
                days = []
                for d in mp.get("days", []):
                    days.append(d.get("abbreviation"))
                loc = mp.get("location")
                meeting_patterns.append({
                    "start_time": mp.get("start_time"),
                    "end_time": mp.get("end_time"),
                    "days": days,
                    "location": loc.get("description") if loc else None
                })

            results.append({
                "number": section.get("number"),
                "component": section.get("component"),
                "class_number": section.get("class_number"),
                "status": section.get("status"),
                "is_open": section.get("status") == "A",
                "enrollment_cap": int(section.get("enrollment_cap", 0)),
                "credits": credits,
                "instructors": instructors,
                "meeting_patterns": meeting_patterns
            })

    return results


def fetch_sections(subject: str, catalog_number: str, term: str) -> list:
    """
    Full structured section list for a course+term (used by /umn/sections).
    Returns [] on any error. Not model-facing.
    """
    return _parse_sections(_get_json(_sections_url(subject, catalog_number, term)))


async def fetch_sections_async(subject: str, catalog_number: str, term: str) -> list:
    """Async twin of fetch_sections — used by the schedule card path."""
    return _parse_sections(await _get_json_async(_sections_url(subject, catalog_number, term)))


# ─── compact summary for the agent ──────────────────────────────────────────

def _fmt_time(t) -> str:
    if not t:
        return ""
    parts = str(t).split(":")
    if len(parts) >= 2:
        hour = parts[0].lstrip("0") or "0"
        return f"{hour}:{parts[1]}"
    return str(t)


def _fmt_meeting(mp: dict) -> str:
    days = "".join(d for d in (mp.get("days") or []) if d)
    st, en = _fmt_time(mp.get("start_time")), _fmt_time(mp.get("end_time"))
    if st or en:
        return f"{days} {st}-{en}".strip()
    return days


def _summarize_sections(results: list, subject: str, catalog_number: str, term: str) -> str:
    if not results:
        return f"No live sections found for {subject.upper()} {catalog_number} in {term}."

    def sort_key(s):
        return (0 if (s.get("component") or "").upper() == "LEC" else 1, s.get("number") or "")

    lines = [f"{subject.upper()} {catalog_number} — {term} ({len(results)} sections):"]
    for s in sorted(results, key=sort_key):
        mps = s.get("meeting_patterns") or []
        when = "; ".join(w for w in (_fmt_meeting(mp) for mp in mps) if w) or "TBA"
        instr = ", ".join(i for i in (s.get("instructors") or []) if i) or "staff"
        loc = next((mp.get("location") for mp in mps if mp.get("location")), None)
        status = "OPEN" if s.get("is_open") else "CLOSED"
        cap = s.get("enrollment_cap")
        parts = [f"Section {s.get('number')} ({s.get('component')})", when, instr]
        if loc:
            parts.append(loc)
        parts.append(status + (f" (cap {cap})" if cap else ""))
        lines.append(" - ".join(parts))
    return "\n".join(lines)


@tool
async def umn_class_sections(subject: str, catalog_number: str, term: str) -> str:
    """
    Live section info for a UMN course.
    Input: subject like "CSCI", catalog_number like "1933", term like "fall 2026".
    Returns one line per section (LEC first): meeting days/times, instructor,
    location, and open/closed status with cap.
    """
    results = await fetch_sections_async(subject, catalog_number, term)
    return _summarize_sections(results, subject, catalog_number, term)
