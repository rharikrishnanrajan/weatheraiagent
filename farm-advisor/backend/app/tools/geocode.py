# ==============================================================================
# AgriPulse: Geocode Tool – City/Place Name → GPS Coordinates
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Calls the free Open-Meteo Geocoding API to convert a place name (like
#    "Fresno, CA" or "Nashik") into latitude and longitude coordinates.
# 2. Exposes `geocode_location` as an agent tool so the AI can auto-resolve
#    any farm location the user mentions in their chat message.
# ==============================================================================

import requests
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool

# Logger for this module – messages will appear in the backend terminal
logger = logging.getLogger("farm_advisor.tools.geocode")

# Open-Meteo's free geocoding API – no API key required
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"


def fetch_geocoding(place_name: str) -> Optional[Dict[str, Any]]:
    """
    Makes a direct HTTP request to the Open-Meteo geocoding service and returns
    the top-ranked location result for the given place name.

    Args:
        place_name: Any location string such as "Des Moines", "Nashik, India",
                    or "Central Valley, California".

    Returns:
        dict: A dictionary with name, latitude, longitude, country, admin1, elevation.
        None: If the place could not be found or the request failed.
    """
    try:
        # Build the API request with the place name and request only 1 result
        response = requests.get(
            GEOCODING_API_URL,
            params={
                "name": place_name,     # The search term (city, village, district)
                "count": 1,            # We only need the single best match
                "language": "en",      # Return names in English
                "format": "json"       # Response format
            },
            timeout=8.0  # Fail fast if the network is slow (8 seconds max)
        )
        response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses
        data = response.json()

        # The API returns a "results" array; grab the first entry if it exists
        results = data.get("results")
        if results and len(results) > 0:
            top = results[0]
            return {
                "name": top.get("name"),                    # Official place name
                "latitude": top.get("latitude"),            # GPS latitude
                "longitude": top.get("longitude"),          # GPS longitude
                "country": top.get("country", ""),         # Country name
                "admin1": top.get("admin1", ""),            # State or province
                "elevation": top.get("elevation", 0.0)     # Elevation in meters
            }
        # No results were returned for this place name
        return None

    except Exception as e:
        logger.error("Geocoding failed for '%s': %s", place_name, e)
        return None


# ==============================================================================
# AGENT TOOL: geocode_location
# ==============================================================================
@tool
def geocode_location(place_name: str) -> Dict[str, Any]:
    """Find the geographic latitude and longitude for a farm location or city name.

    This tool is called by the AI agent whenever a user mentions a location name
    (e.g. "Fresno, CA") and no coordinates are yet known. The resolved coordinates
    are then passed to weather or irrigation tools.

    Args:
        place_name: The name of the town, district, city, or region
                    (e.g., 'Fresno, CA', 'Des Moines', 'Nashik').
    """
    # Attempt to fetch GPS coordinates from the geocoding service
    res = fetch_geocoding(place_name)

    if not res:
        # Inform the AI that the place name was not recognized
        return {
            "status": "not_found",
            "message": (
                f"Could not find coordinates for '{place_name}'. "
                "Please verify the spelling or provide coordinates manually."
            )
        }

    # Return the resolved coordinates and location metadata
    return {
        "status": "success",
        "location": res
    }
