import os
import json
import httpx
import redis as redis_client

from urllib.parse import urlencode
from langchain.tools import tool


def _get_redis():
    return redis_client.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True
    )
    
    
async def _get_json(url: str, timeout: int = 12) -> dict:
    
    r = _get_redis()
    cached = r.get(url)
    
    if cached:
        print(f"[CACHE HIT] {url}")
        return json.loads(cached)
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"User-Agent": "gophergpt/1.0"}, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            print(f"[CACHE MISS] {url}")
            r.setex(url, 60 * 60 * 6, json.dumps(data)) # 6 hours in seconds
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


@tool
async def umn_class_sections(subject: str, catalog_number: str, term: str) -> str:
    """
    Get live section info for a UMN course.
    Input: subject like "CSCI", catalog_number like "1933", term like "fall 2026"
    Output: JSON string with section details including schedule, instructor, and open/closed status.
    """

    sterm = resolve_sterm(term)
    url = f"https://courses.umn.edu/campuses/UMNTC/terms/{sterm}/courses.json?q=catalog_number={catalog_number},subject_id={subject.upper()}"

    data = await _get_json(url)
    if "success" in data and data["success"] is False:
        return json.dumps(data)
    
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

    return json.dumps(results, ensure_ascii=False)
