# ==============================================================================
# AgriPulse: Weather API Endpoint (GET /api/weather)
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Resolves coordinates via Open-Meteo Geocoding if a city name is provided.
# 2. Falls back to the registered farm profile coordinates if none are specified.
# 3. Pulls current conditions, 7-day daily forecasts, and hourly time-series data.
# 4. Runs automated hazard detection algorithms (Frost, Heatwaves, High Wind, Rain).
# ==============================================================================

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query

# Database profile loader
from app.db.session import get_farm_profile

# Weather and Geocoding tools
from app.tools.geocode import fetch_geocoding
from app.tools.weather import fetch_open_meteo_data, get_weather_desc, detect_weather_hazards

logger = logging.getLogger("farm_advisor.api.weather")

# Router mounted at /api/weather
router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("", response_model=Dict[str, Any])
def get_weather_data(
    lat: Optional[float] = Query(None, description="GPS Latitude"),
    lon: Optional[float] = Query(None, description="GPS Longitude"),
    place_name: Optional[str] = Query(None, description="City, state, or farm location name"),
    days: int = Query(7, ge=1, le=14, description="Forecast duration in days (1 to 14)")
):
    """
    GET /api/weather
    Returns full weather analytics for the specified location or default farm.
    
    Data returned includes:
    - Current temperature, humidity, wind, and precipitation.
    - 7-day daily forecast (highs, lows, evapotranspiration ET0, UV index).
    - 24-48 hour hourly trends for interactive charts.
    - Active agricultural hazard alerts (Frost warnings, Heat stress).
    """
    try:
        resolved_lat = lat
        resolved_lon = lon
        location_title = place_name or "Farm Location"
        country = ""
        admin1 = ""
        elevation = 0.0

        # Step 1: If a place name is provided but coordinates are missing, geocode it
        if place_name and (resolved_lat is None or resolved_lon is None):
            geo = fetch_geocoding(place_name)
            if geo:
                resolved_lat = geo["latitude"]
                resolved_lon = geo["longitude"]
                location_title = f"{geo['name']}, {geo.get('admin1', '')}".strip(", ")
                country = geo.get("country", "")
                admin1 = geo.get("admin1", "")
                elevation = geo.get("elevation", 0.0)
            else:
                logger.warning("Geocoding failed for '%s', falling back to farm profile", place_name)

        # Step 2: If coordinates are still missing, use the registered farm profile from SQLite
        if resolved_lat is None or resolved_lon is None:
            profile = get_farm_profile()
            resolved_lat = profile.get("latitude", 38.5816)
            resolved_lon = profile.get("longitude", -121.4944)
            location_title = profile.get("location_name", "Sacramento, California")

        # Step 3: Fetch real-time forecast data from the free Open-Meteo API
        raw_data = fetch_open_meteo_data(resolved_lat, resolved_lon, days=days)
        current = raw_data.get("current", {})
        daily = raw_data.get("daily", {})
        hourly = raw_data.get("hourly", {})

        # Step 4: Format current snapshot
        current_formatted = {
            "time": current.get("time", ""),
            "temperature_2m": current.get("temperature_2m", 0.0),
            "relative_humidity_2m": current.get("relative_humidity_2m", 0.0),
            "apparent_temperature": current.get("apparent_temperature", 0.0),
            "precipitation": current.get("precipitation", 0.0),
            "rain": current.get("rain", 0.0),
            "weather_code": current.get("weather_code", 0),
            "weather_description": get_weather_desc(current.get("weather_code", 0)),
            "cloud_cover": current.get("cloud_cover", 0.0),
            "wind_speed_10m": current.get("wind_speed_10m", 0.0),
            "wind_gusts_10m": current.get("wind_gusts_10m", 0.0),
            "wind_direction_10m": current.get("wind_direction_10m", 0.0)
        }

        # Step 5: Format daily forecast array (temperatures, precipitation, ET0)
        daily_items: List[Dict[str, Any]] = []
        d_times = daily.get("time", [])
        for i in range(len(d_times)):
            wcode = daily.get("weather_code", [])[i] if i < len(daily.get("weather_code", [])) else 0
            daily_items.append({
                "date": d_times[i],
                "weather_code": wcode,
                "weather_description": get_weather_desc(wcode),
                "temperature_2m_max": daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max", [])) else 0.0,
                "temperature_2m_min": daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min", [])) else 0.0,
                "precipitation_sum": daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else 0.0,
                "precipitation_probability_max": daily.get("precipitation_probability_max", [])[i] if i < len(daily.get("precipitation_probability_max", [])) else 0,
                "wind_speed_10m_max": daily.get("wind_speed_10m_max", [])[i] if i < len(daily.get("wind_speed_10m_max", [])) else 0.0,
                "et0_fao_evapotranspiration": daily.get("et0_fao_evapotranspiration", [])[i] if i < len(daily.get("et0_fao_evapotranspiration", [])) else 0.0,
                "uv_index_max": daily.get("uv_index_max", [])[i] if i < len(daily.get("uv_index_max", [])) else 0.0,
            })

        # Step 6: Format hourly series (first 48 hours for temperature & precipitation graphs)
        hourly_items: List[Dict[str, Any]] = []
        h_times = hourly.get("time", [])[:48]
        for i in range(len(h_times)):
            hourly_items.append({
                "time": h_times[i],
                "temperature_2m": hourly.get("temperature_2m", [])[i] if i < len(hourly.get("temperature_2m", [])) else 0.0,
                "precipitation": hourly.get("precipitation", [])[i] if i < len(hourly.get("precipitation", [])) else 0.0,
                "precipitation_probability": hourly.get("precipitation_probability", [])[i] if i < len(hourly.get("precipitation_probability", [])) else 0,
                "relative_humidity_2m": hourly.get("relative_humidity_2m", [])[i] if i < len(hourly.get("relative_humidity_2m", [])) else 0.0,
                "wind_speed_10m": hourly.get("wind_speed_10m", [])[i] if i < len(hourly.get("wind_speed_10m", [])) else 0.0
            })

        # Step 7: Detect hazardous agricultural conditions
        alerts = detect_weather_hazards(raw_data)

        # Step 8: Return structured API response
        return {
            "location": {
                "name": location_title,
                "latitude": resolved_lat,
                "longitude": resolved_lon,
                "country": country,
                "admin1": admin1,
                "elevation": elevation,
                "timezone": raw_data.get("timezone", "UTC")
            },
            "current": current_formatted,
            "daily": daily_items,
            "hourly": hourly_items,
            "alerts": alerts
        }
    except Exception as e:
        logger.error("Failed to retrieve weather for lat=%s lon=%s: %s", lat, lon, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Weather retrieval failed: {str(e)}")
