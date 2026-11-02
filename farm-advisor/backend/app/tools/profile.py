# ==============================================================================
# AgriPulse: Farm Profile Tools – Read & Update Farmer Profile
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. `get_farm_profile` – reads the farmer's stored profile from the SQLite database.
# 2. `update_farm_profile` – writes changes (new crops, soil type, location) back to the DB.
#
# BEGINNER TIP: The "farm profile" is like a settings file that tells the AI about
# your specific farm: where it is, what soil you have, and what crops you grow.
# These tools let the AI read and update that profile during a conversation.
# ==============================================================================

import logging
from typing import Dict, Any, Optional, List
from langchain_core.tools import tool

# Database helper functions (defined in app/db/session.py)
from app.db.session import get_farm_profile as db_get_profile, update_farm_profile as db_update_profile

logger = logging.getLogger("farm_advisor.tools.profile")


# ==============================================================================
# AGENT TOOL: get_farm_profile
# ==============================================================================
@tool
def get_farm_profile() -> Dict[str, Any]:
    """Retrieve the registered farm profile, including location, coordinates,
    crops grown, soil type, irrigation type, and farm size."""
    try:
        # Delegate to the database layer to load the current profile row
        profile = db_get_profile()
        return {
            "status": "success",
            "profile": profile   # Full dictionary of all farm fields
        }
    except Exception as e:
        logger.error("Failed to read farm profile: %s", e)
        return {
            "status": "error",
            "message": f"Could not retrieve farm profile: {str(e)}"
        }


# ==============================================================================
# AGENT TOOL: update_farm_profile
# ==============================================================================
@tool
def update_farm_profile(
    location_name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    crops: Optional[List[str]] = None,
    soil_type: Optional[str] = None,
    irrigation_type: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Update attributes in the farm profile when the farmer provides new details
    about their location, crops, soil, or irrigation.

    Args:
        location_name: Name of location or city (e.g. 'Fresno, California').
        latitude: Geographic latitude decimal (e.g. 36.74).
        longitude: Geographic longitude decimal (e.g. -119.77).
        crops: Full list of crops grown on the farm (e.g. ['Tomato', 'Corn']).
        soil_type: Soil classification ('Sandy', 'Loamy', 'Clay', 'Silt').
        irrigation_type: Irrigation method ('Drip', 'Sprinkler', 'Flood', 'Rainfed').
        notes: Additional farm notes or agronomy preferences.
    """
    try:
        # Build a dictionary of only the fields the caller wants to update
        # (None values are skipped – we don't overwrite fields not mentioned)
        updates = {}
        if location_name is not None:
            updates["location_name"] = location_name
        if latitude is not None:
            updates["latitude"] = latitude
        if longitude is not None:
            updates["longitude"] = longitude
        if crops is not None:
            updates["crops"] = crops        # Replaces the full crops list
        if soil_type is not None:
            updates["soil_type"] = soil_type
        if irrigation_type is not None:
            updates["irrigation_type"] = irrigation_type
        if notes is not None:
            updates["notes"] = notes

        # Write the changes to the SQLite database
        updated = db_update_profile(updates)
        return {
            "status": "success",
            "message": "Farm profile updated successfully.",
            "profile": updated   # Return the full updated profile for confirmation
        }
    except Exception as e:
        logger.error("Failed to update farm profile: %s", e)
        return {
            "status": "error",
            "message": f"Could not update farm profile: {str(e)}"
        }
