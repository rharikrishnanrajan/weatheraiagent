# ==============================================================================
# AgriPulse: Farm Profile API Endpoint (GET/PUT /api/profile)
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Allows viewing and editing the farmer's profile (name, location, crops, soil).
# 2. Persists all profile modifications into the SQLite database.
# 3. Ensures the AI agent has up-to-date context when giving farming advice.
# ==============================================================================

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.schemas.profile import FarmProfileUpdate
from app.db.session import get_farm_profile, update_farm_profile

logger = logging.getLogger("farm_advisor.api.profile")

# Router mounted at /api/profile
router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=Dict[str, Any])
def read_profile():
    """
    GET /api/profile
    Retrieves the current farmer and soil profile from the database.
    """
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
    """
    PUT /api/profile (also accepts POST)
    Updates specific fields in the farmer profile (e.g. changing soil from Clay to Loamy,
    updating crops grown, or changing the farm's GPS coordinates).
    """
    try:
        # exclude_unset=True ensures we only overwrite fields provided in the request
        update_data = payload.model_dump(exclude_unset=True)
        updated = update_farm_profile(update_data)
        return updated
    except Exception as e:
        logger.error("Error updating profile: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
