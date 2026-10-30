from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class FarmProfileBase(BaseModel):
    farmer_name: str = Field(default="Farmer", description="Farmer or farm name")
    location_name: str = Field(default="Sacramento, California", description="Name of the farm location")
    latitude: float = Field(default=38.5816, description="Latitude coordinate")
    longitude: float = Field(default=-121.4944, description="Longitude coordinate")
    crops: List[str] = Field(default_factory=lambda: ["Tomato", "Corn", "Wheat"], description="List of crops currently grown")
    field_size_hectares: float = Field(default=12.5, description="Size of farm in hectares")
    soil_type: str = Field(default="Loamy", description="Predominant soil type: Sandy, Loamy, Clay, Silt, Peat")
    irrigation_type: str = Field(default="Drip", description="Irrigation method: Drip, Sprinkler, Flood, Rainfed")
    preferred_language: str = Field(default="en", description="Preferred language code (e.g. en, es, hi)")
    notes: Optional[str] = Field(default="Standard seasonal rotation with organic pest management practices.", description="Extra farm notes")

class FarmProfileUpdate(BaseModel):
    farmer_name: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    crops: Optional[List[str]] = None
    field_size_hectares: Optional[float] = None
    soil_type: Optional[str] = None
    irrigation_type: Optional[str] = None
    preferred_language: Optional[str] = None
    notes: Optional[str] = None

class FarmProfile(FarmProfileBase):
    id: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
