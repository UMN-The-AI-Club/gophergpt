import json
import re
import httpx
from html.parser import HTMLParser
from urllib.parse import quote
from langchain.tools import tool

_LIBCAL_BASE = "https://libcal.lib.umn.edu"
_RESERVATIONS = "https://reservations.umn.edu"
_STUDY_SPACE_FINDER = "https://studyspace.umn.edu"

# UMN Libraries LibCal location IDs (lid parameter on the spaces page)
_LIBRARY_LOCATION_IDS = {
    "walter": 3604,
    "walter library": 3604,
    "wilson": 3605,
    "wilson library": 3605,
    "andersen": 3606,
    "andersen library": 3606,
    "magrath": 3607,
    "magrath library": 3607,
    "o'brien": 3608,
    "health sciences": 3609,
    "bio-medical library": 3609,
    "biomedical": 3609,
    "architecture": 3610,
    "architecture library": 3610,
}

# Known building name → campus map slug
_CAMPUS_MAP_SLUGS = {
    "walter library": "walter-library",
    "walter": "walter-library",
    "wilson library": "wilson-library",
    "wilson": "wilson-library",
    "andersen library": "andersen-library",
    "andersen": "andersen-library",
    "magrath library": "magrath-library",
    "magrath": "magrath-library",
    "keller hall": "keller-hall",
    "keller": "keller-hall",
    "coffman": "coffman-memorial-union",
    "coffman memorial union": "coffman-memorial-union",
    "tate": "tate-laboratory-of-physics",
    "tate hall": "tate-laboratory-of-physics",
    "ford hall": "ford-hall",
    "ford": "ford-hall",
    "smith hall": "smith-hall",
    "pillsbury hall": "pillsbury-hall",
    "pillsbury": "pillsbury-hall",
    "vincent hall": "vincent-hall",
    "vincent": "vincent-hall",
    "science teaching": "science-teaching-student-services",
    "stss": "science-teaching-student-services",
    "blegen hall": "blegen-hall",
    "blegen": "blegen-hall",
    "liberal arts": "liberal-arts-building",
    "mayo": "mayo-memorial-building",
    "mayo memorial": "mayo-memorial-building",
    "lind hall": "lind-hall",
    "lind": "lind-hall",
    "bruininks hall": "bruininks-hall",
    "bruininks": "bruininks-hall",
    "appleby hall": "appleby-hall",
    "appleby": "appleby-hall",
    "morrill hall": "morrill-hall",
    "morrill": "morrill-hall",
}


def _directions_links(building_name: str) -> dict:
    """Return Google Maps and UMN campus map links for a building."""
    key = building_name.strip().lower()
    query = f"{building_name} University of Minnesota"
    google_maps = f"https://www.google.com/maps/search/{quote(query)}"

    slug = _CAMPUS_MAP_SLUGS.get(key)
    if not slug:
        # Best-effort: convert name to hyphenated slug
        slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
    campus_map = f"https://campusmaps.umn.edu/{slug}"

    return {
        "google_maps": google_maps,
        "campus_map": campus_map,
    }


class _LibCalHTMLParser(HTMLParser):
    """Minimal parser to pull space names and booking links from LibCal spaces pages."""

    def __init__(self):
        super().__init__()
        self.rooms = []
        self._in_space_name = False
        self._current_name = None
        self._current_url = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href", "")

        # LibCal renders each space as an <a> whose href is /space/{id}
        if tag == "a" and "/space/" in href:
            self._current_url = href if href.startswith("http") else f"{_LIBCAL_BASE}{href}"
            self._in_space_name = True

    def handle_data(self, data):
        if self._in_space_name and data.strip():
            self._current_name = data.strip()
            self._in_space_name = False
            if self._current_name and self._current_url:
                self.rooms.append({
                    "name": self._current_name,
                    "booking_link": self._current_url,
                })
                self._current_name = None
                self._current_url = None

    def handle_endtag(self, tag):
        if tag == "a":
            self._in_space_name = False


async def _fetch_libcal_spaces(lid: int) -> list:
    """Fetch the public LibCal spaces page for a given location ID and return room list."""
    url = f"{_LIBCAL_BASE}/spaces?lid={lid}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; gophergpt/1.0)"}, timeout=15)
            html = resp.text
    except Exception:
        return []

    parser = _LibCalHTMLParser()
    parser.feed(html)

    seen = set()
    unique = []
    for room in parser.rooms:
        key = room["booking_link"]
        if key not in seen:
            seen.add(key)
            unique.append(room)
    return unique


@tool
async def umn_room_booking(building_name: str) -> str:
    """
    Look up bookable rooms/study spaces in a UMN building, with directions.
    Input: a building name (e.g., "Walter Library", "Coffman", "Keller Hall").
    Output: JSON with room names, booking links, directions (Google Maps + UMN campus map),
            and a link to the UMN Study Space Finder.
    Use this whenever a user asks about booking, reserving, finding rooms, or getting
    directions to a UMN building or study space.
    """
    key = building_name.strip().lower()
    directions = _directions_links(building_name)
    dir_line = f"Directions: Google Maps {directions['google_maps']} | Campus Map {directions['campus_map']}"

    # --- Library buildings: scrape LibCal (public, no auth needed) ---
    lid = _LIBRARY_LOCATION_IDS.get(key)
    if lid:
        rooms = await _fetch_libcal_spaces(lid)
        booking_url = f"{_LIBCAL_BASE}/spaces?lid={lid}"
        lines = [
            f"{building_name} — bookable study rooms (UMN Libraries LibCal).",
            dir_line,
            f"Reserve a room: {booking_url} (log in with your UMN x500).",
        ]
        if rooms:
            names = ", ".join(r["name"] for r in rooms[:6])
            extra = f" (+{len(rooms) - 6} more)" if len(rooms) > 6 else ""
            lines.append(f"Rooms include: {names}{extra}.")
        lines.append(f"Browse all campus study spaces: {_STUDY_SPACE_FINDER}")
        return "\n".join(lines)

    # --- Non-library buildings: 25Live ---
    browse_url = f"https://25live.collegenet.com/pro/umn#!/home/location/list?&search={quote(building_name)}"
    return "\n".join([
        f"{building_name} — rooms are managed through 25Live.",
        dir_line,
        f"Browse spaces: {browse_url}",
        f"Submit a request: {_RESERVATIONS} (log in with your UMN x500).",
        f"Browse all campus study spaces: {_STUDY_SPACE_FINDER}",
    ])
