from pydantic import BaseModel, Field
from typing import List, Optional

class WeatherLocation(BaseModel):
    name: str
    latitude: float
    longitude: float
    country: Optional[str] = None
    admin1: Optional[str] = None
    elevation: Optional[float] = None

class CurrentWeather(BaseModel):
    time: str
    temperature_2m: float
    relative_humidity_2m: float
    apparent_temperature: float
    precipitation: float
    rain: float
    weather_code: int
    weather_description: str
    cloud_cover: float
    wind_speed_10m: float
    wind_gusts_10m: float
    wind_direction_10m: float

class DailyForecastItem(BaseModel):
    date: str
    weather_code: int
    weather_description: str
    temperature_2m_max: float
    temperature_2m_min: float
    apparent_temperature_max: float
    apparent_temperature_min: float
    precipitation_sum: float
    precipitation_probability_max: Optional[float] = None
    wind_speed_10m_max: float
    et0_fao_evapotranspiration: Optional[float] = None
    uv_index_max: Optional[float] = None

class HourlyForecastItem(BaseModel):
    time: str
    temperature_2m: float
    relative_humidity_2m: float
    precipitation_probability: float
    precipitation: float
    wind_speed_10m: float
    wind_gusts_10m: float
    soil_temperature_0cm: Optional[float] = None
    soil_moisture_0_to_1cm: Optional[float] = None

class WeatherAlert(BaseModel):
    category: str = Field(description="Frost, Heatwave, Heavy Rain, Strong Winds, High Humidity")
    severity: str = Field(description="Low, Moderate, High, Severe")
    title: str
    description: str
    action_recommendation: str
    valid_time: Optional[str] = None

class WeatherResponse(BaseModel):
    location: WeatherLocation
    current: CurrentWeather
    daily: List[DailyForecastItem]
    hourly_recent_or_upcoming: List[HourlyForecastItem]
    alerts: List[WeatherAlert]
