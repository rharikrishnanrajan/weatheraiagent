import requests
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool

logger = logging.getLogger("farm_advisor.tools.geocode")

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"

def fetch_geocoding(place_name: str) -> Optional[Dict[str, Any]]:
    """Query Open-Meteo Geocoding API for place coordinates."""
    try:
        response = requests.get(
            GEOCODING_API_URL,
            params={
                "name": place_name,
                "count": 1,
                "language": "en",
                "format": "json"
            },
            timeout=8.0
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results")
        if results and len(results) > 0:
            top = results[0]
            return {
                "name": top.get("name"),
                "latitude": top.get("latitude"),
                "longitude": top.get("longitude"),
                "country": top.get("country", ""),
                "admin1": top.get("admin1", ""),
                "elevation": top.get("elevation", 0.0)
            }
        return None
    except Exception as e:
        logger.error("Geocoding failed for '%s': %s", place_name, e)
        return None

@tool
def geocode_location(place_name: str) -> Dict[str, Any]:
    """Find the geographic latitude and longitude for a farm location or city name.
    
    Args:
        place_name: The name of the town, district, city, or region (e.g., 'Fresno, CA', 'Des Moines', 'Nashik').
    """
    res = fetch_geocoding(place_name)
    if not res:
        return {
            "status": "not_found",
            "message": f"Could not find coordinates for '{place_name}'. Please verify the spelling or provide coordinates."
        }
    return {
        "status": "success",
        "location": res
    }
