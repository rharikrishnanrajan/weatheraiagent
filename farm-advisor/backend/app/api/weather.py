import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query

from app.db.session import get_farm_profile
from app.tools.geocode import fetch_geocoding
from app.tools.weather import fetch_open_meteo_data, get_weather_desc, detect_weather_hazards

logger = logging.getLogger("farm_advisor.api.weather")
router = APIRouter(prefix="/weather", tags=["Weather"])

@router.get("", response_model=Dict[str, Any])
def get_weather_data(
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    place_name: Optional[str] = Query(None, description="City or farm location name"),
    days: int = Query(7, ge=1, le=14, description="Forecast days")
):
    """Retrieve full live weather conditions, 7-day agronomic forecast, hourly series, and hazard alerts."""
    try:
        resolved_lat = lat
        resolved_lon = lon
        location_title = place_name or "Farm Location"
        country = ""
        admin1 = ""
        elevation = 0.0

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

        if resolved_lat is None or resolved_lon is None:
            profile = get_farm_profile()
            resolved_lat = profile.get("latitude", 38.5816)
            resolved_lon = profile.get("longitude", -121.4944)
            location_title = profile.get("location_name", "Sacramento, California")

        raw_data = fetch_open_meteo_data(resolved_lat, resolved_lon, days=days)
        current = raw_data.get("current", {})
        daily = raw_data.get("daily", {})
        hourly = raw_data.get("hourly", {})

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
                "apparent_temperature_max": daily.get("apparent_temperature_max", [])[i] if i < len(daily.get("apparent_temperature_max", [])) else 0.0,
                "apparent_temperature_min": daily.get("apparent_temperature_min", [])[i] if i < len(daily.get("apparent_temperature_min", [])) else 0.0,
                "precipitation_sum": daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else 0.0,
                "precipitation_probability_max": daily.get("precipitation_probability_max", [])[i] if i < len(daily.get("precipitation_probability_max", [])) else 0.0,
                "wind_speed_10m_max": daily.get("wind_speed_10m_max", [])[i] if i < len(daily.get("wind_speed_10m_max", [])) else 0.0,
                "et0_fao_evapotranspiration": daily.get("et0_fao_evapotranspiration", [])[i] if i < len(daily.get("et0_fao_evapotranspiration", [])) else 0.0,
                "uv_index_max": daily.get("uv_index_max", [])[i] if i < len(daily.get("uv_index_max", [])) else 0.0
            })

        # Next 24-48 hours hourly
        hourly_items: List[Dict[str, Any]] = []
        h_times = hourly.get("time", [])[:48]
        for idx in range(len(h_times)):
            hourly_items.append({
                "time": h_times[idx],
                "temperature_2m": hourly.get("temperature_2m", [])[idx] if idx < len(hourly.get("temperature_2m", [])) else 0.0,
                "relative_humidity_2m": hourly.get("relative_humidity_2m", [])[idx] if idx < len(hourly.get("relative_humidity_2m", [])) else 0.0,
                "precipitation_probability": hourly.get("precipitation_probability", [])[idx] if idx < len(hourly.get("precipitation_probability", [])) else 0.0,
                "precipitation": hourly.get("precipitation", [])[idx] if idx < len(hourly.get("precipitation", [])) else 0.0,
                "wind_speed_10m": hourly.get("wind_speed_10m", [])[idx] if idx < len(hourly.get("wind_speed_10m", [])) else 0.0,
                "wind_gusts_10m": hourly.get("wind_gusts_10m", [])[idx] if idx < len(hourly.get("wind_gusts_10m", [])) else 0.0,
                "soil_temperature_0cm": hourly.get("soil_temperature_0cm", [])[idx] if idx < len(hourly.get("soil_temperature_0cm", [])) else None,
                "soil_moisture_0_to_1cm": hourly.get("soil_moisture_0_to_1cm", [])[idx] if idx < len(hourly.get("soil_moisture_0_to_1cm", [])) else None
            })

        alerts = detect_weather_hazards(raw_data)

        return {
            "location": {
                "name": location_title,
                "latitude": resolved_lat,
                "longitude": resolved_lon,
                "country": country,
                "admin1": admin1,
                "elevation": elevation
            },
            "current": current_formatted,
            "daily": daily_items,
            "hourly_recent_or_upcoming": hourly_items,
            "alerts": alerts
        }

    except Exception as e:
        logger.error("Error fetching weather: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather: {str(e)}")
