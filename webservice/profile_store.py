import json
import os

DATA_DIR = os.getenv("DATA_DIR", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)

PROFILES_PATH = os.path.join(DATA_DIR, "profiles.json")


def init_store():
    if not os.path.exists(PROFILES_PATH):
        with open(PROFILES_PATH, "w") as f:
            json.dump({}, f)


def _read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_profile(user_id: str) -> dict:
    profiles = _read_json(PROFILES_PATH)
    if not isinstance(profiles, dict):
        profiles = {}
    return profiles.get(
        user_id,
        {
            "user_id": user_id,
            "major": "",
            "level": "",
            "year": "",
            "personalization_notes": "",
        },
    )


def save_profile(user_id: str, profile_data: dict) -> dict:
    profiles = _read_json(PROFILES_PATH)
    if not isinstance(profiles, dict):
        profiles = {}
    profiles[user_id] = {
        "user_id": user_id,
        "major": profile_data.get("major", ""),
        "level": profile_data.get("level", ""),
        "year": profile_data.get("year", ""),
        "personalization_notes": profile_data.get("personalization_notes", ""),
    }
    _write_json(PROFILES_PATH, profiles)
    return profiles[user_id]
