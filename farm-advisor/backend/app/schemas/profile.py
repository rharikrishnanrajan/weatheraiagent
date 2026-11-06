# ==============================================================================
# AgriPulse: Farm Profile Schemas (Pydantic Models)
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Validates farmer profile information (crops grown, soil texture, irrigation system).
# 2. Defines default values so new users can test immediately without manual setup.
# 3. Models partial updates when a farmer modifies specific settings via the UI.
# ==============================================================================

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime


class FarmProfileBase(BaseModel):
    """Core farm profile attributes shared between read and write models."""
    farmer_name: str = Field(default="Farmer", description="Farmer or farm enterprise name")
    location_name: str = Field(default="Sacramento, California", description="Name of the farm location/region")
    latitude: float = Field(default=38.5816, description="Latitude coordinate in decimal degrees")
    longitude: float = Field(default=-121.4944, description="Longitude coordinate in decimal degrees")
    crops: List[str] = Field(
        default_factory=lambda: ["Tomato", "Corn", "Wheat"],
        description="List of crops currently under cultivation"
    )
    field_size_hectares: float = Field(default=12.5, description="Total farmed area in hectares (1 ha ≈ 2.47 acres)")
    soil_type: str = Field(default="Loamy", description="Predominant soil texture: 'Sandy', 'Loamy', 'Clay', or 'Silt'")
    irrigation_type: str = Field(default="Drip", description="Irrigation method: 'Drip', 'Sprinkler', 'Flood', or 'Rainfed'")
    preferred_language: str = Field(default="en", description="Two-letter language code (e.g. 'en', 'es', 'hi')")
    notes: Optional[str] = Field(
        default="Standard seasonal rotation with organic pest management practices.",
        description="Optional agronomic notes or field history"
    )


class FarmProfileUpdate(BaseModel):
    """Payload for updating farm profile. All fields optional so partial updates work."""
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
    """Full database record including auto-managed IDs and timestamps."""
    id: int = 1
    created_at: datetime
    updated_at: datetime

    # Configures Pydantic to read data directly from ORM/database row objects
    model_config = ConfigDict(from_attributes=True)
