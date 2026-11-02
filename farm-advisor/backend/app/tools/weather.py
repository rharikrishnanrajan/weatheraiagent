# ==============================================================================
# AgriPulse: Weather Tool – Live Forecast Fetcher & Hazard Detector
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Fetches live weather data from the free Open-Meteo API (no API key needed).
# 2. Converts WMO weather codes (numbers like 65, 80) into readable descriptions.
# 3. Detects dangerous agricultural conditions: frost, heatwaves, heavy rain, gales.
# 4. Exposes two agent tools: get_weather_forecast and get_weather_alerts.
# ==============================================================================

import requests
import logging
from typing import Dict, Any, List
from langchain_core.tools import tool

# Standard Python logging - gives us timestamped messages in the terminal
logger = logging.getLogger("farm_advisor.tools.weather")

# The URL of the free Open-Meteo forecast API (no API key required)
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# ------------------------------------------------------------------------------
# WMO WEATHER CODE LOOKUP TABLE
# ------------------------------------------------------------------------------
# The Open-Meteo API returns numeric weather codes defined by the
# World Meteorological Organization (WMO). This dictionary maps each code
# to a human-readable description for display in the UI and AI responses.
WMO_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def get_weather_desc(code: int) -> str:
    """
    Translates a numeric WMO weather code into a plain English description.

    Args:
        code: WMO numeric weather code (e.g. 65 = Heavy rain).

    Returns:
        str: Human-readable description (e.g. "Heavy rain").
    """
    # Look up the code in our dictionary; return a fallback string if not found
    return WMO_CODE_MAP.get(code, f"Weather code {code}")


def fetch_open_meteo_data(lat: float, lon: float, days: int = 7) -> Dict[str, Any]:
    """
    Makes an HTTP GET request to Open-Meteo to download current conditions,
    daily agricultural forecast, and hourly soil/weather series data.

    Args:
        lat: Latitude of the farm in decimal degrees (e.g. 38.58).
        lon: Longitude of the farm in decimal degrees (e.g. -121.49).
        days: How many days of forecast to request (1–14).

    Returns:
        dict: Full raw JSON response from Open-Meteo (current, daily, hourly).

    Raises:
        requests.HTTPError: If the API returns a non-200 status code.
    """
    # Build the query parameters for the Open-Meteo API request
    params = {
        "latitude": lat,
        "longitude": lon,
        # --- Current Conditions ---
        "current": [
            "temperature_2m",           # Air temperature 2m above ground (°C)
            "relative_humidity_2m",     # Relative humidity % at 2m
            "apparent_temperature",     # Feels-like (wind chill / heat index)
            "precipitation",            # Current precipitation (mm)
            "rain",                     # Liquid rain component (mm)
            "weather_code",             # WMO numeric code for sky condition
            "cloud_cover",              # Cloud cover percentage (0–100%)
            "wind_speed_10m",           # Wind speed at 10m height (km/h)
            "wind_gusts_10m",           # Maximum wind gusts at 10m (km/h)
            "wind_direction_10m"        # Wind direction in degrees (0=North)
        ],
        # --- Daily Summary ---
        "daily": [
            "weather_code",
            "temperature_2m_max",               # Daytime maximum temperature (°C)
            "temperature_2m_min",               # Nighttime minimum temperature (°C)
            "apparent_temperature_max",
            "apparent_temperature_min",
            "precipitation_sum",                # Total rainfall for the day (mm)
            "precipitation_probability_max",    # Max chance of rain (0–100%)
            "wind_speed_10m_max",               # Maximum wind speed for the day
            "et0_fao_evapotranspiration",       # Reference ET₀ (FAO-56) in mm/day
            "uv_index_max"                      # Peak UV index
        ],
        # --- Hourly Series ---
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "wind_speed_10m",
            "wind_gusts_10m",
            "soil_temperature_0cm",             # Soil surface temperature (°C)
            "soil_moisture_0_to_1cm"            # Volumetric soil moisture (0-1 cm depth)
        ],
        "timezone": "auto",                     # Auto-detect local timezone from coordinates
        "forecast_days": min(max(days, 1), 14)  # Clamp between 1 and 14 days
    }

    # Send the HTTP GET request and raise an error on bad status codes
    response = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()


def detect_weather_hazards(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Scans the forecast data for dangerous agricultural conditions and produces
    a structured list of alert objects with category, severity, and recommended actions.

    Hazards checked:
    - Frost / Hard Freeze (min temp ≤ 2.5°C)
    - Heatwave / Heat Stress (max temp ≥ 34°C)
    - Heavy Rainfall (daily sum ≥ 20 mm)
    - Gale / Strong Wind (max wind ≥ 45 km/h)
    - Prolonged High Humidity (≥ 85% for 16+ hours in next 48h) → Disease window

    Args:
        data: Raw Open-Meteo JSON (dict containing 'daily' and 'hourly' keys).

    Returns:
        List[dict]: List of alert dictionaries, each with keys:
            category, severity, title, description, action_recommendation, valid_time.
    """
    alerts = []

    # Extract daily arrays from the forecast data
    daily = data.get("daily", {})
    dates = daily.get("time", [])                   # List of date strings e.g. ['2026-11-01', ...]
    t_min = daily.get("temperature_2m_min", [])     # Daily minimum temperatures
    t_max = daily.get("temperature_2m_max", [])     # Daily maximum temperatures
    precip = daily.get("precipitation_sum", [])     # Total rain per day (mm)
    wind_max = daily.get("wind_speed_10m_max", [])  # Daily peak wind speed

    # Scan the next 7 days for agricultural hazards
    for i in range(min(len(dates), 7)):
        day_date = dates[i]
        # Use safe list indexing with fallback defaults in case arrays are shorter than expected
        min_temp = t_min[i] if i < len(t_min) else 15.0
        max_temp = t_max[i] if i < len(t_max) else 25.0
        rain = precip[i] if i < len(precip) else 0.0
        wind = wind_max[i] if i < len(wind_max) else 10.0

        # ------------------------------------------------------------------
        # HAZARD 1: FROST (min temp at or below freezing)
        # ------------------------------------------------------------------
        if min_temp <= 0.0:
            # Hard freeze – most crops will suffer tissue damage
            alerts.append({
                "category": "Frost",
                "severity": "Severe",
                "title": f"Hard Freeze Alert on {day_date}",
                "description": f"Predicted minimum temperature of {min_temp}°C threatens frost damage to tender crops and blossoms.",
                "action_recommendation": "Deploy row covers, frost fleece, or operate overhead sprinkler/wind machines prior to dawn.",
                "valid_time": day_date
            })
        elif min_temp <= 2.5:
            # Light frost – low-lying pockets are at greatest risk
            alerts.append({
                "category": "Frost",
                "severity": "Moderate",
                "title": f"Light Frost Risk on {day_date}",
                "description": f"Minimum temperature dropping to {min_temp}°C. Ground frost possible in low-lying pockets.",
                "action_recommendation": "Protect nursery beds and sensitive seedlings. Delay morning irrigation if freezing is imminent.",
                "valid_time": day_date
            })

        # ------------------------------------------------------------------
        # HAZARD 2: HEATWAVE (max temp causes crop heat stress)
        # ------------------------------------------------------------------
        if max_temp >= 38.0:
            # Severe heat: blossom drop, pollen sterility, rapid wilting
            alerts.append({
                "category": "Heatwave",
                "severity": "Severe",
                "title": f"Severe Heat Stress Alert on {day_date}",
                "description": f"High temperatures reaching {max_temp}°C can induce blossom drop, pollination failure, and severe heat wilt.",
                "action_recommendation": "Provide adequate pre-irrigation during early morning. Consider shade cloth or anti-transpirant sprays.",
                "valid_time": day_date
            })
        elif max_temp >= 34.0:
            # Moderate heat: accelerated soil moisture loss
            alerts.append({
                "category": "Heatwave",
                "severity": "Moderate",
                "title": f"Heat Stress Warning on {day_date}",
                "description": f"Anticipated high of {max_temp}°C may cause rapid soil moisture depletion.",
                "action_recommendation": "Monitor soil moisture closely and schedule supplemental watering in the early morning.",
                "valid_time": day_date
            })

        # ------------------------------------------------------------------
        # HAZARD 3: HEAVY RAIN (soil saturation & spray wash-off risk)
        # ------------------------------------------------------------------
        if rain >= 35.0:
            alerts.append({
                "category": "Heavy Rain",
                "severity": "High",
                "title": f"Heavy Rainfall & Flood Risk on {day_date}",
                "description": f"Forecast predicts {rain:.1f} mm of rainfall. Soil saturation and surface runoff likely.",
                "action_recommendation": "Clear drainage ditches, secure low-lying field access, and cease all field tractor operations to prevent soil compaction.",
                "valid_time": day_date
            })
        elif rain >= 20.0:
            alerts.append({
                "category": "Heavy Rain",
                "severity": "Moderate",
                "title": f"Moderate Rain Watch on {day_date}",
                "description": f"Expected rainfall of {rain:.1f} mm. High likelihood of wet foliage and spray wash-off.",
                "action_recommendation": "Delay scheduled pesticide/fertilizer applications. Natural rainfall will meet irrigation needs.",
                "valid_time": day_date
            })

        # ------------------------------------------------------------------
        # HAZARD 4: HIGH WIND (spray drift, crop lodging)
        # ------------------------------------------------------------------
        if wind >= 45.0:
            alerts.append({
                "category": "Strong Winds",
                "severity": "High",
                "title": f"Gale / Strong Wind Warning on {day_date}",
                "description": f"Wind gusts predicted to reach {wind:.1f} km/h. Lodging hazard for tall crops (corn, wheat).",
                "action_recommendation": "Do not apply spray chemicals. Secure polytunnels, trellises, and support tall crops if feasible.",
                "valid_time": day_date
            })

    # ------------------------------------------------------------------
    # HAZARD 5: PROLONGED HIGH HUMIDITY (fungal disease window)
    # Checks the first 48 hourly readings for sustained high-humidity periods
    # ------------------------------------------------------------------
    hourly = data.get("hourly", {})
    hum_list = hourly.get("relative_humidity_2m", [])[:48]  # Limit to next 48 hours
    if hum_list:
        # Count hours where relative humidity is ≥ 85% (optimal for spore germination)
        high_hum_count = sum(1 for h in hum_list if h >= 85)
        if high_hum_count >= 16:
            # 16+ hours of high humidity is a meaningful disease window
            alerts.append({
                "category": "High Humidity",
                "severity": "Moderate",
                "title": "Prolonged High Humidity & Disease Window",
                "description": f"Relative humidity exceeds 85% for {high_hum_count} hours in the next 48h, favoring spore germination.",
                "action_recommendation": "Scout susceptible crops for fungal symptoms (downy/powdery mildew, blight). Prepare prophylactic bio-fungicide if suitable.",
                "valid_time": "Next 48 Hours"
            })

    return alerts


# ==============================================================================
# AGENT TOOL: get_weather_forecast
# ==============================================================================
@tool
def get_weather_forecast(lat: float, lon: float, days: int = 7) -> Dict[str, Any]:
    """Retrieve live current weather and daily agronomic forecast for given geographic coordinates.

    Args:
        lat: Latitude of the farm (e.g. 38.58).
        lon: Longitude of the farm (e.g. -121.49).
        days: Number of forecast days to retrieve (1 to 14, default 7).
    """
    try:
        # Step 1: Fetch raw forecast JSON from Open-Meteo
        data = fetch_open_meteo_data(lat, lon, days)
        current = data.get("current", {})
        daily = data.get("daily", {})

        # Step 2: Build a clean summary of current conditions
        current_summary = {
            "time": current.get("time"),
            "temperature_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "apparent_temp_c": current.get("apparent_temperature"),
            "precipitation_mm": current.get("precipitation"),
            "condition": get_weather_desc(current.get("weather_code", 0)),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "wind_gusts_kmh": current.get("wind_gusts_10m")
        }

        # Step 3: Build daily forecast list (one entry per day)
        daily_list = []
        dates = daily.get("time", [])
        for i in range(len(dates)):
            daily_list.append({
                "date": dates[i],
                "condition": get_weather_desc(daily.get("weather_code", [])[i]),
                "temp_max_c": daily.get("temperature_2m_max", [])[i],
                "temp_min_c": daily.get("temperature_2m_min", [])[i],
                "rain_sum_mm": daily.get("precipitation_sum", [])[i],
                "precip_probability": daily.get("precipitation_probability_max", [])[i],
                "wind_max_kmh": daily.get("wind_speed_10m_max", [])[i],
                "et0_evapotranspiration_mm": daily.get("et0_fao_evapotranspiration", [])[i]
            })

        # Step 4: Detect any active agricultural hazard alerts
        alerts = detect_weather_hazards(data)

        return {
            "status": "success",
            "current": current_summary,
            "daily_forecast": daily_list,
            "hazard_alerts": alerts
        }
    except Exception as e:
        logger.error("Weather forecast fetch error: %s", e)
        return {
            "status": "error",
            "message": f"Failed to retrieve weather data: {str(e)}"
        }


# ==============================================================================
# AGENT TOOL: get_weather_alerts
# ==============================================================================
@tool
def get_weather_alerts(lat: float, lon: float) -> Dict[str, Any]:
    """Check for active or forecasted weather hazard alerts (frost, heatwaves, heavy downpours, strong winds) for a farm.

    Args:
        lat: Latitude of the farm.
        lon: Longitude of the farm.
    """
    try:
        # Fetch forecast data and extract only the hazard alerts
        data = fetch_open_meteo_data(lat, lon, days=7)
        alerts = detect_weather_hazards(data)
        return {
            "status": "success",
            "alert_count": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Could not compute alerts: {str(e)}"
        }
