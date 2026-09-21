from fastapi import APIRouter
from pydantic import BaseModel

from webservice.profile_store import get_profile, save_profile

router = APIRouter()

class ProfileRequest(BaseModel):
    """Request model for profile update endpoint."""
    user_id: str
    major: str = ""
    level: str = ""
    year: str = ""
    personalization_notes: str = ""

@router.get("/profile")
def get_profile_endpoint(user_id: str):
    """
    Retrieves a user's profile by user_id.

    Args:
        user_id: the unique identifier for the user

    Returns:
        a dict with ok status and the user's profile
    """
    profile = get_profile(user_id)
    return {"ok": True, "profile": profile}

@router.put("/profile")
def update_profile_endpoint(request: ProfileRequest):
    """
    Creates or updates a user's profile.

    Args:
        request: ProfileRequest containing user_id, major, year, and personalization_notes

    Returns:
        a dict with ok status and the updated profile
    """
    profile = save_profile(request.user_id, {
        "major": request.major,
        "level": request.level,
        "year": request.year,
        "personalization_notes": request.personalization_notes,
    })
    return {"ok": True, "profile": profile}