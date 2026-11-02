# ==============================================================================
# AgriPulse: Irrigation Advisor Tool (FAO-56 Evapotranspiration Model)
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Calculates daily crop water loss (ETc = ET0 * Kc) according to UN FAO-56 standards.
# 2. Factors in soil holding capacity (Sandy, Loamy, Clay) to prevent under/over-watering.
# 3. Analyzes upcoming 3-day rainfall to advise whether to IRRIGATE, REDUCE, or HOLD.
# ==============================================================================

import logging
from typing import Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger("farm_advisor.tools.irrigation")

# Crop coefficient (Kc) lookup table across different growth stages
# Kc represents how much water a specific crop uses compared to grass reference ET0
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

# Fallback crop coefficient if a crop is not in the dictionary
DEFAULT_KC = {"initial": 0.45, "vegetative": 0.75, "flowering": 1.10, "reproductive": 1.10, "maturity": 0.65}

# Physical water-holding and infiltration attributes per soil type
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
    
    # Step 1: Look up crop coefficient factor (Kc)
    crop_table = CROP_KC_TABLE.get(crop_lower, DEFAULT_KC)
    kc = crop_table.get(stage_lower)
    if kc is None:
        # Match nearest stage keyword
        for key in crop_table:
            if key in stage_lower or stage_lower in key:
                kc = crop_table[key]
                break
    if kc is None:
        kc = 0.85  # General mid-season average fallback
        
    # Step 2: Compute daily crop water demand (ETc = ET0 * Kc)
    daily_crop_water_loss = round(et0_mm * kc, 2)
    three_day_demand = round(daily_crop_water_loss * 3.0, 2)
    
    # Step 3: Compute net water deficit accounting for effective rainfall
    effective_forecast_rain = forecast_rain_mm * 0.8  # Assume 80% effective infiltration
    effective_recent_rain = recent_rain_mm * 0.7
    
    net_water_deficit = round(three_day_demand - effective_forecast_rain - effective_recent_rain, 2)
    
    # Step 4: Soil characteristics
    soil_info = SOIL_CHARACTERISTICS.get(soil_lower, SOIL_CHARACTERISTICS["loamy"])
    base_dose = soil_info["recommended_dose_mm"]
    
    # Step 5: Formulate actionable agronomic recommendation
    if forecast_rain_mm >= 15.0:
        action = "HOLD_IRRIGATION"
        recommendation = (
            f"HOLD IRRIGATION. Significant rainfall ({forecast_rain_mm:.1f} mm) is forecasted within 72 hours. "
            f"Anticipated rain exceeds 3-day crop demand ({three_day_demand:.1f} mm). "
            f"Hold off to prevent waterlogging, nutrient leaching, and root hypoxia."
        )
        water_amount_mm = 0.0
    elif net_water_deficit <= 2.0:
        action = "DELAY_OR_LIGHT"
        recommendation = (
            f"DELAY OR LIGHT CYCLE. Light rain or residual soil moisture covers current demand. "
            f"Net deficit is only {net_water_deficit:.1f} mm. Monitor topsoil before irrigating."
        )
        water_amount_mm = 0.0
    elif net_water_deficit > base_dose:
        action = "IRRIGATE_FULL"
        water_amount_mm = min(net_water_deficit, base_dose * 1.3)
        recommendation = (
            f"IRRIGATE. Cumulative crop evapotranspiration ({three_day_demand:.1f} mm) is outpacing rainfall. "
            f"Apply approximately {water_amount_mm:.1f} mm over {soil_info['frequency']} to replenish root zone field capacity."
        )
    else:
        action = "IRRIGATE_MAINTENANCE"
        water_amount_mm = net_water_deficit
        recommendation = (
            f"APPLY MAINTENANCE IRRIGATION. Supply {water_amount_mm:.1f} mm to keep soil moisture within optimal tension."
        )
        
    return {
        "crop": crop.capitalize(),
        "growth_stage": growth_stage,
        "soil_type": soil_type.capitalize(),
        "kc_factor": kc,
        "reference_et0_mm_day": et0_mm,
        "daily_crop_water_loss_mm": daily_crop_water_loss,
        "three_day_crop_demand_mm": three_day_demand,
        "forecast_rain_3d_mm": forecast_rain_mm,
        "net_deficit_mm": max(0.0, net_water_deficit),
        "action": action,
        "recommended_dose_mm": round(water_amount_mm, 1),
        "soil_notes": soil_info["note"],
        "recommendation": recommendation,
        "source": "irrigation_management_guide.md"
    }
