import logging
from typing import Dict, Any, Optional, List
from langchain_core.tools import tool
from app.db.session import get_farm_profile as db_get_profile, update_farm_profile as db_update_profile

logger = logging.getLogger("farm_advisor.tools.profile")

@tool
def get_farm_profile() -> Dict[str, Any]:
    """Retrieve the registered farm profile, including location, coordinates, crops grown, soil type, irrigation type, and farm size."""
    try:
        profile = db_get_profile()
        return {
            "status": "success",
            "profile": profile
        }
    except Exception as e:
        logger.error("Failed to read farm profile: %s", e)
        return {
            "status": "error",
            "message": f"Could not retrieve farm profile: {str(e)}"
        }

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
    """Update attributes in the farm profile when the farmer provides new details about their location, crops, soil, or irrigation.
    
    Args:
        location_name: Name of location or city.
        latitude: Geographic latitude.
        longitude: Geographic longitude.
        crops: List of crops grown on the farm (e.g. ['Tomato', 'Corn']).
        soil_type: Soil classification ('Sandy', 'Loamy', 'Clay', 'Silt').
        irrigation_type: Irrigation method ('Drip', 'Sprinkler', 'Flood', 'Rainfed').
        notes: Additional farm notes or agronomy preferences.
    """
    try:
        updates = {}
        if location_name is not None:
            updates["location_name"] = location_name
        if latitude is not None:
            updates["latitude"] = latitude
        if longitude is not None:
            updates["longitude"] = longitude
        if crops is not None:
            updates["crops"] = crops
        if soil_type is not None:
            updates["soil_type"] = soil_type
        if irrigation_type is not None:
            updates["irrigation_type"] = irrigation_type
        if notes is not None:
            updates["notes"] = notes
            
        updated = db_update_profile(updates)
        return {
            "status": "success",
            "message": "Farm profile updated successfully.",
            "profile": updated
        }
    except Exception as e:
        logger.error("Failed to update farm profile: %s", e)
        return {
            "status": "error",
            "message": f"Could not update farm profile: {str(e)}"
        }
