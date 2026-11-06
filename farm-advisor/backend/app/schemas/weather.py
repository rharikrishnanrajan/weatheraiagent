# ==============================================================================
# AgriPulse: Weather Data Schemas (Pydantic Models)
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Models GPS location details resolved by Open-Meteo Geocoding.
# 2. Defines current weather metrics (temperature, humidity, wind, rainfall).
# 3. Models daily agronomic projections (highs, lows, evapotranspiration ET0, UV index).
# 4. Formats hourly series data for frontend interactive temperature/precipitation charts.
# ==============================================================================

from pydantic import BaseModel, Field
from typing import List, Optional


class WeatherLocation(BaseModel):
    """Geographic information for the queried location."""
    name: str = Field(description="Resolved place name (e.g. 'Sacramento, California')")
    latitude: float = Field(description="Latitude coordinate in decimal degrees")
    longitude: float = Field(description="Longitude coordinate in decimal degrees")
    country: Optional[str] = Field(default=None, description="Country name")
    admin1: Optional[str] = Field(default=None, description="State, province, or primary administrative division")
    elevation: Optional[float] = Field(default=None, description="Elevation above sea level in meters")


class CurrentWeather(BaseModel):
    """Real-time meteorological snapshot."""
    time: str = Field(description="Observation ISO timestamp")
    temperature_2m: float = Field(description="Air temperature at 2 meters above ground in Celsius")
    relative_humidity_2m: float = Field(description="Relative humidity percentage (0-100%)")
    apparent_temperature: float = Field(description="Feels-like temperature in Celsius")
    precipitation: float = Field(description="Current precipitation intensity in mm")
    rain: float = Field(description="Current liquid rain in mm")
    weather_code: int = Field(description="WMO numeric weather code")
    weather_description: str = Field(description="Human-readable condition (e.g., 'Partly cloudy')")
    cloud_cover: float = Field(description="Total cloud cover percentage (0-100%)")
    wind_speed_10m: float = Field(description="Wind speed at 10 meters in km/h")
    wind_gusts_10m: float = Field(description="Peak wind gusts at 10 meters in km/h")
    wind_direction_10m: float = Field(description="Wind direction in degrees (0-360°)")


class DailyForecastItem(BaseModel):
    """Day-by-day forecast projection for agricultural planning."""
    date: str = Field(description="Date string (YYYY-MM-DD)")
    weather_code: int = Field(description="WMO weather code for the day")
    weather_description: str = Field(description="Readable description of expected conditions")
    temperature_2m_max: float = Field(description="Maximum daytime temperature in Celsius")
    temperature_2m_min: float = Field(description="Minimum overnight temperature in Celsius")
    apparent_temperature_max: float = Field(description="Maximum apparent temperature in Celsius")
    apparent_temperature_min: float = Field(description="Minimum apparent temperature in Celsius")
    precipitation_sum: float = Field(description="Total expected rainfall/snow for the 24-hour period in mm")
    precipitation_probability_max: Optional[float] = Field(default=None, description="Highest probability of rain (0-100%)")
    wind_speed_10m_max: float = Field(description="Maximum sustained wind speed in km/h")
    et0_fao_evapotranspiration: Optional[float] = Field(default=None, description="Reference FAO-56 crop evapotranspiration in mm/day")
    uv_index_max: Optional[float] = Field(default=None, description="Peak UV index")


class HourlyForecastItem(BaseModel):
    """Hourly time-series point used for charts and spray safety analysis."""
    time: str = Field(description="ISO timestamp of the hourly observation/forecast")
    temperature_2m: float = Field(description="Temperature in Celsius")
    relative_humidity_2m: float = Field(description="Relative humidity percentage")
    precipitation_probability: float = Field(description="Rain probability percentage")
    precipitation: float = Field(description="Precipitation quantity in mm")
    wind_speed_10m: float = Field(description="Wind speed in km/h")
    wind_gusts_10m: float = Field(description="Wind gusts in km/h")
    soil_temperature_0cm: Optional[float] = Field(default=None, description="Topsoil surface temperature in Celsius")
    soil_moisture_0_to_1cm: Optional[float] = Field(default=None, description="Surface volumetric soil moisture (m³/m³)")


class WeatherAlertItem(BaseModel):
    """Severe weather hazard detected by automated agronomic safety rules."""
    event: str = Field(description="Alert headline (e.g. 'FROST HAZARD', 'HIGH WIND ADVISORY')")
    severity: str = Field(description="Alert tier: 'WARNING', 'WATCH', or 'ADVISORY'")
    description: str = Field(description="Agronomic consequences and preventive action advice")
    start_time: str = Field(description="Start time of hazardous period")
    end_time: str = Field(description="Estimated conclusion of hazardous period")
