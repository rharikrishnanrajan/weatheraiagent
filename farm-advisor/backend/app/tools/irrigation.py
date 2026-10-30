import logging
from typing import Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger("farm_advisor.tools.irrigation")

CROP_KC_TABLE = {
    "tomato": {"initial": 0.45, "vegetative": 0.75, "flowering": 1.15, "fruiting": 1.15, "ripening": 0.80},
    "corn": {"initial": 0.40, "vegetative": 0.80, "silking": 1.20, "flowering": 1.20, "maturity": 0.60},
    "maize": {"initial": 0.40, "vegetative": 0.80, "flowering": 1.20, "grain_fill": 1.10, "maturity": 0.60},
    "wheat": {"initial": 0.35, "tillering": 0.75, "flowering": 1.15, "heading": 1.15, "ripening": 0.45},
    "rice": {"initial": 1.05, "tillering": 1.10, "flowering": 1.20, "panicle": 1.20, "ripening": 0.90},
    "potato": {"initial": 0.50, "vegetative": 0.80, "tuber_bulking": 1.15, "flowering": 1.10, "maturity": 0.70},
    "soybean": {"initial": 0.40, "vegetative": 0.75, "flowering": 1.10, "pod_fill": 1.10, "maturity": 0.50},
    "cotton": {"initial": 0.45, "vegetative": 0.75, "flowering": 1.15, "boll_formation": 1.20, "maturity": 0.65},
    "onion": {"initial": 0.40, "vegetative": 0.70, "bulb_enlargement": 1.05, "maturity": 0.75},
}

DEFAULT_KC = {"initial": 0.45, "vegetative": 0.75, "flowering": 1.10, "reproductive": 1.10, "maturity": 0.65}

SOIL_CHARACTERISTICS = {
    "sandy": {
        "holding_capacity": "Low (25-35 mm/m)",
        "frequency": "Frequent, small applications",
        "recommended_dose_mm": 12.0,
        "note": "Water percolates rapidly. Avoid deep saturation to prevent fertilizer leaching."
    },
    "loamy": {
        "holding_capacity": "Medium-High (60-80 mm/m)",
        "frequency": "Balanced, every 3-5 days",
        "recommended_dose_mm": 25.0,
        "note": "Ideal structure for moisture retention and root aeration."
    },
    "clay": {
        "holding_capacity": "High (80-100 mm/m)",
        "frequency": "Infrequent, slow deep soak",
        "recommended_dose_mm": 28.0,
        "note": "Slow infiltration rate. Apply at low flow rates or pulse to avoid pooling and runoff."
    },
    "silt": {
        "holding_capacity": "High (70-90 mm/m)",
        "frequency": "Moderate",
        "recommended_dose_mm": 22.0,
        "note": "Good moisture holding, prone to surface crusting after sprinkler irrigation."
    }
}

@tool
def irrigation_advisor(
    crop: str,
    growth_stage: str,
    soil_type: str,
    forecast_rain_mm: float,
    et0_mm: float = 4.0,
    recent_rain_mm: float = 0.0
) -> Dict[str, Any]:
    """Calculate crop-specific irrigation demand using FAO-56 evapotranspiration models and forecasted rainfall.
    
    Args:
        crop: Crop name (e.g., 'Tomato', 'Corn', 'Wheat', 'Potato', 'Rice').
        growth_stage: Current stage ('initial', 'vegetative', 'flowering', 'fruiting', 'maturity').
        soil_type: Type of soil ('Sandy', 'Loamy', 'Clay', 'Silt').
        forecast_rain_mm: Expected total rain over the next 3 days (mm).
        et0_mm: Reference evapotranspiration per day (mm/day, default 4.0 mm/day).
        recent_rain_mm: Rainfall received in the last 48 hours (mm, default 0.0).
    """
    crop_lower = crop.lower().strip()
    stage_lower = growth_stage.lower().strip()
    soil_lower = soil_type.lower().strip()
    
    # 1. Determine Kc factor
    crop_table = CROP_KC_TABLE.get(crop_lower, DEFAULT_KC)
    kc = crop_table.get(stage_lower)
    if kc is None:
        # Match nearest stage keyword
        for key in crop_table:
            if key in stage_lower or stage_lower in key:
                kc = crop_table[key]
                break
    if kc is None:
        kc = 0.85 # default moderate Kc
        
    # 2. Daily and 3-day evapotranspiration (ETc)
    daily_etc = round(et0_mm * kc, 2)
    period_days = 3
    total_water_demand = round(daily_etc * period_days, 2)
    
    # 3. Effective precipitation credit (approx 75% of forecast rain, 60% of recent rain)
    effective_rain = (forecast_rain_mm * 0.75) + (recent_rain_mm * 0.60)
    net_irrigation_needed = max(0.0, round(total_water_demand - effective_rain, 1))
    
    # 4. Soil recommendations
    soil_info = SOIL_CHARACTERISTICS.get(soil_lower, SOIL_CHARACTERISTICS["loamy"])
    
    # 5. Decision recommendation
    if forecast_rain_mm >= 15.0:
        recommendation = "HOLD IRRIGATION"
        reason = f"Upcoming forecast predicts {forecast_rain_mm} mm of rain, which will sufficiently replenish root zone moisture without irrigation."
        suggested_mm = 0.0
    elif net_irrigation_needed <= 3.0:
        recommendation = "DELAY / OPTIONAL"
        reason = f"Soil moisture and minor rainfall satisfy crop demand ({total_water_demand} mm needed vs {effective_rain:.1f} mm effective rain). Inspect field moisture before watering."
        suggested_mm = 0.0
    else:
        recommendation = "IRRIGATE"
        # Dose capped by soil holding capacity
        suggested_mm = min(net_irrigation_needed, soil_info["recommended_dose_mm"])
        reason = f"Crop evapotranspiration ({total_water_demand} mm over 3 days) exceeds effective rainfall ({effective_rain:.1f} mm). Deficit of {net_irrigation_needed} mm should be replenished."

    m3_per_hectare = round(suggested_mm * 10, 1) # 1 mm = 10 m3/ha
    
    return {
        "crop": crop,
        "growth_stage": growth_stage,
        "soil_type": soil_type,
        "crop_coefficient_kc": kc,
        "daily_crop_et_mm": daily_etc,
        "three_day_demand_mm": total_water_demand,
        "effective_rain_mm": round(effective_rain, 1),
        "net_deficit_mm": net_irrigation_needed,
        "action": recommendation,
        "suggested_application_depth_mm": suggested_mm,
        "water_volume_m3_per_hectare": m3_per_hectare,
        "best_timing": "Early morning (6:00 AM - 9:00 AM) or dusk to minimize evaporative loss",
        "soil_advice": f"{soil_info['frequency']}. {soil_info['note']}",
        "explanation": reason
    }
