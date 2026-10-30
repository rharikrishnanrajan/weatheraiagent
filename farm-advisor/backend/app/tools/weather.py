import requests
import logging
from typing import Dict, Any, List
from langchain_core.tools import tool

logger = logging.getLogger("farm_advisor.tools.weather")

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

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
    return WMO_CODE_MAP.get(code, f"Weather code {code}")

def fetch_open_meteo_data(lat: float, lon: float, days: int = 7) -> Dict[str, Any]:
    """Fetch raw forecast data from Open-Meteo API."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "rain",
            "weather_code",
            "cloud_cover",
            "wind_speed_10m",
            "wind_gusts_10m",
            "wind_direction_10m"
        ],
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "apparent_temperature_max",
            "apparent_temperature_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "et0_fao_evapotranspiration",
            "uv_index_max"
        ],
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "wind_speed_10m",
            "wind_gusts_10m",
            "soil_temperature_0cm",
            "soil_moisture_0_to_1cm"
        ],
        "timezone": "auto",
        "forecast_days": min(max(days, 1), 14)
    }
    
    response = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()

def detect_weather_hazards(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Analyze forecast data and detect severe agronomic hazards."""
    alerts = []
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    t_min = daily.get("temperature_2m_min", [])
    t_max = daily.get("temperature_2m_max", [])
    precip = daily.get("precipitation_sum", [])
    wind_max = daily.get("wind_speed_10m_max", [])
    
    # Check next 3-7 days
    for i in range(min(len(dates), 7)):
        day_date = dates[i]
        min_temp = t_min[i] if i < len(t_min) else 15.0
        max_temp = t_max[i] if i < len(t_max) else 25.0
        rain = precip[i] if i < len(precip) else 0.0
        wind = wind_max[i] if i < len(wind_max) else 10.0
        
        # Frost Hazard
        if min_temp <= 0.0:
            alerts.append({
                "category": "Frost",
                "severity": "Severe",
                "title": f"Hard Freeze Alert on {day_date}",
                "description": f"Predicted minimum temperature of {min_temp}°C threatens frost damage to tender crops and blossoms.",
                "action_recommendation": "Deploy row covers, frost fleece, or operate overhead sprinkler/wind machines prior to dawn.",
                "valid_time": day_date
            })
        elif min_temp <= 2.5:
            alerts.append({
                "category": "Frost",
                "severity": "Moderate",
                "title": f"Light Frost Risk on {day_date}",
                "description": f"Minimum temperature dropping to {min_temp}°C. Ground frost possible in low-lying pockets.",
                "action_recommendation": "Protect nursery beds and sensitive seedlings. Delay morning irrigation if freezing is imminent.",
                "valid_time": day_date
            })
            
        # Extreme Heat Hazard
        if max_temp >= 38.0:
            alerts.append({
                "category": "Heatwave",
                "severity": "Severe",
                "title": f"Severe Heat Stress Alert on {day_date}",
                "description": f"High temperatures reaching {max_temp}°C can induce blossom drop, pollination failure, and severe heat wilt.",
                "action_recommendation": "Provide adequate pre-irrigation during early morning. Consider shade cloth or anti-transpirant sprays.",
                "valid_time": day_date
            })
        elif max_temp >= 34.0:
            alerts.append({
                "category": "Heatwave",
                "severity": "Moderate",
                "title": f"Heat Stress Warning on {day_date}",
                "description": f"Anticipated high of {max_temp}°C may cause rapid soil moisture depletion.",
                "action_recommendation": "Monitor soil moisture closely and schedule supplemental watering in the early morning.",
                "valid_time": day_date
            })
            
        # Heavy Rain Hazard
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
            
        # High Wind Hazard
        if wind >= 45.0:
            alerts.append({
                "category": "Strong Winds",
                "severity": "High",
                "title": f"Gale / Strong Wind Warning on {day_date}",
                "description": f"Wind gusts predicted to reach {wind:.1f} km/h. Lodging hazard for tall crops (corn, wheat).",
                "action_recommendation": "Do not apply spray chemicals. Secure polytunnels, trellises, and support tall crops if feasible.",
                "valid_time": day_date
            })

    # Hourly high humidity check for prolonged fungal danger
    hourly = data.get("hourly", {})
    hum_list = hourly.get("relative_humidity_2m", [])[:48]
    if hum_list:
        high_hum_count = sum(1 for h in hum_list if h >= 85)
        if high_hum_count >= 16:
            alerts.append({
                "category": "High Humidity",
                "severity": "Moderate",
                "title": "Prolonged High Humidity & Disease Window",
                "description": f"Relative humidity exceeds 85% for {high_hum_count} hours in the next 48h, favoring spore germination.",
                "action_recommendation": "Scout susceptible crops for fungal symptoms (downy/powdery mildew, blight). Prepare prophylactic bio-fungicide if suitable.",
                "valid_time": "Next 48 Hours"
            })
            
    return alerts

@tool
def get_weather_forecast(lat: float, lon: float, days: int = 7) -> Dict[str, Any]:
    """Retrieve live current weather and daily agronomic forecast for given geographic coordinates.
    
    Args:
        lat: Latitude of the farm (e.g. 38.58).
        lon: Longitude of the farm (e.g. -121.49).
        days: Number of forecast days to retrieve (1 to 14, default 7).
    """
    try:
        data = fetch_open_meteo_data(lat, lon, days)
        current = data.get("current", {})
        daily = data.get("daily", {})
        
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

@tool
def get_weather_alerts(lat: float, lon: float) -> Dict[str, Any]:
    """Check for active or forecasted weather hazard alerts (frost, heatwaves, heavy downpours, strong winds) for a farm.
    
    Args:
        lat: Latitude of the farm.
        lon: Longitude of the farm.
    """
    try:
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
