import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.schemas.profile import FarmProfileUpdate
from app.db.session import get_farm_profile, update_farm_profile

logger = logging.getLogger("farm_advisor.api.profile")
router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("", response_model=Dict[str, Any])
def read_profile():
    """Retrieve the current farm profile."""
    try:
        profile = get_farm_profile()
        if not profile:
            raise HTTPException(status_code=404, detail="Farm profile not found.")
        return profile
    except Exception as e:
        logger.error("Error reading profile: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("", response_model=Dict[str, Any])
@router.post("", response_model=Dict[str, Any])
def modify_profile(payload: FarmProfileUpdate):
    """Update fields of the farm profile."""
    try:
        update_data = payload.model_dump(exclude_unset=True)
        updated = update_farm_profile(update_data)
        return updated
    except Exception as e:
        logger.error("Error updating profile: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
