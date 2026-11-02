# ==============================================================================
# AgriPulse: Irrigation Advisor Tool (FAO-56 Evapotranspiration Model)
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Calculates daily crop water loss (ETc = ET0 * Kc) according to UN FAO-56 standards.
#    - ET0: Reference Evapotranspiration – how fast grass loses water.
#    - Kc:  Crop Coefficient – a multiplier showing how thirsty a specific crop is.
#    - ETc: Crop Evapotranspiration = ET0 × Kc (actual water need for the crop).
# 2. Factors in soil holding capacity (Sandy, Loamy, Clay) to prevent under/over-watering.
# 3. Analyzes upcoming 3-day rainfall to advise whether to IRRIGATE, REDUCE, or HOLD.
#
# BEGINNER TIP: Think of this tool like a "crop water calculator". It tells you:
# "Given your soil type, how thirsty is your crop TODAY, and will upcoming rain cover it?"
# ==============================================================================

import logging
from typing import Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger("farm_advisor.tools.irrigation")

# ==============================================================================
# CROP COEFFICIENT (Kc) TABLE
# ==============================================================================
# Each crop has different water requirements at different growth stages.
# Kc multiplies the reference grass ET0 to get the actual crop water need.
# Example: Tomato at Flowering: ETc = ET0 × 1.15 (needs 15% more water than grass)
# Source: FAO Irrigation and Drainage Paper No. 56 (Allen et al., 1998)
CROP_KC_TABLE = {
    "tomato": {
        "initial": 0.45,        # Seedling stage - small leaf area, less water needed
        "vegetative": 0.75,     # Canopy expanding - moderate water demand
        "flowering": 1.15,      # Critical stage - peak water use, drought stress = yield loss
        "fruiting": 1.15,       # Fruit fill - sustained peak demand
        "ripening": 0.80        # Drying down - reduced water need before harvest
    },
    "corn": {
        "initial": 0.40,
        "vegetative": 0.80,
        "silking": 1.20,        # Silking (pollination) - highest water sensitivity in corn
        "flowering": 1.20,
        "maturity": 0.60        # Grain-fill & dent stage - irrigation can taper off
    },
    "maize": {
        "initial": 0.40,
        "vegetative": 0.80,
        "flowering": 1.20,
        "grain_fill": 1.10,
        "maturity": 0.60
    },
    "wheat": {
        "initial": 0.35,
        "tillering": 0.75,
        "flowering": 1.15,
        "heading": 1.15,        # Flag leaf and ear filling - most yield-critical period
        "ripening": 0.45        # Grain drying - no irrigation needed
    },
    "rice": {
        "initial": 1.05,        # Rice is unique - paddy requires standing water from the start
        "tillering": 1.10,
        "flowering": 1.20,
        "panicle": 1.20,
        "ripening": 0.90
    },
    "potato": {
        "initial": 0.50,
        "vegetative": 0.80,
        "tuber_bulking": 1.15,  # Tuber swell phase - critical water period for yield
        "flowering": 1.10,
        "maturity": 0.70
    },
    "soybean": {
        "initial": 0.40,
        "vegetative": 0.75,
        "flowering": 1.10,
        "pod_fill": 1.10,       # Pod fill (R3-R6) - most critical drought period
        "maturity": 0.50
    },
    "cotton": {
        "initial": 0.45,
        "vegetative": 0.75,
        "flowering": 1.15,
        "boll_formation": 1.20, # Boll set and fill - peak water demand in cotton
        "maturity": 0.65
    },
    "onion": {
        "initial": 0.40,
        "vegetative": 0.70,
        "bulb_enlargement": 1.05,   # Bulbing stage - moderate-high water needed
        "maturity": 0.75
    },
}

# Default Kc values used for any crop not listed in the table above
DEFAULT_KC = {
    "initial": 0.45,
    "vegetative": 0.75,
    "flowering": 1.10,
    "reproductive": 1.10,
    "maturity": 0.65
}

# ==============================================================================
# SOIL CHARACTERISTICS TABLE
# ==============================================================================
# Different soil types hold and drain water at very different rates.
# Sandy soils drain fast (frequent, small doses needed).
# Clay soils drain slow (infrequent, large doses – but risk waterlogging).
SOIL_CHARACTERISTICS = {
    "sandy": {
        "holding_capacity": "Low (25-35 mm/m)",
        "frequency": "Frequent, small applications",   # Water often, less per time
        "recommended_dose_mm": 12.0,                  # Apply only 12mm per irrigation event
        "note": "Water percolates rapidly. Avoid deep saturation to prevent fertilizer leaching."
    },
    "loamy": {
        "holding_capacity": "Medium-High (60-80 mm/m)",
        "frequency": "Balanced, every 3-5 days",
        "recommended_dose_mm": 25.0,                  # Apply 25mm per event
        "note": "Ideal structure for moisture retention and root aeration."
    },
    "clay": {
        "holding_capacity": "High (80-100 mm/m)",
        "frequency": "Infrequent, slow deep soak",
        "recommended_dose_mm": 28.0,                  # Apply 28mm but very slowly
        "note": "Slow infiltration rate. Apply at low flow rates or pulse to avoid pooling and runoff."
    },
    "silt": {
        "holding_capacity": "High (70-90 mm/m)",
        "frequency": "Moderate",
        "recommended_dose_mm": 22.0,
        "note": "Good moisture holding, prone to surface crusting after sprinkler irrigation."
    }
}


# ==============================================================================
# AGENT TOOL: irrigation_advisor
# ==============================================================================
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
    # Normalize inputs to lowercase for dictionary lookups
    crop_lower = crop.lower().strip()
    stage_lower = growth_stage.lower().strip()
    soil_lower = soil_type.lower().strip()

    # ------------------------------------------------------------------
    # STEP 1: Look up Crop Coefficient (Kc) for this crop and stage
    # ------------------------------------------------------------------
    crop_table = CROP_KC_TABLE.get(crop_lower, DEFAULT_KC)
    kc = crop_table.get(stage_lower)   # Try exact stage name match first

    if kc is None:
        # If exact match fails, try partial/substring matching
        # e.g. "tuber bulking" will match "tuber_bulking"
        for key in crop_table:
            if key in stage_lower or stage_lower in key:
                kc = crop_table[key]
                break

    if kc is None:
        # If no match at all, use 0.85 (mid-season average across most crops)
        kc = 0.85

    # ------------------------------------------------------------------
    # STEP 2: Calculate daily crop water demand
    # Formula: ETc (mm/day) = ET0 × Kc
    # Then multiply by 3 for a 3-day planning horizon
    # ------------------------------------------------------------------
    daily_crop_water_loss = round(et0_mm * kc, 2)       # Daily crop water need (mm/day)
    three_day_demand = round(daily_crop_water_loss * 3.0, 2)  # 3-day total demand (mm)

    # ------------------------------------------------------------------
    # STEP 3: Compute net water deficit accounting for effective rainfall
    # Not all rainfall is absorbed – some runs off or evaporates before penetrating.
    # We assume 80% of forecast rain and 70% of recent rain is "effective" (absorbed).
    # ------------------------------------------------------------------
    effective_forecast_rain = forecast_rain_mm * 0.8    # 80% of upcoming rain enters soil
    effective_recent_rain = recent_rain_mm * 0.7        # 70% of recent rain credited

    # Net deficit = how much more water the crop needs beyond what rain provides
    net_water_deficit = round(three_day_demand - effective_forecast_rain - effective_recent_rain, 2)

    # ------------------------------------------------------------------
    # STEP 4: Get soil-specific recommended dose
    # ------------------------------------------------------------------
    soil_info = SOIL_CHARACTERISTICS.get(soil_lower, SOIL_CHARACTERISTICS["loamy"])
    base_dose = soil_info["recommended_dose_mm"]  # Standard dose for this soil

    # ------------------------------------------------------------------
    # STEP 5: Formulate the irrigation recommendation
    # Priority: if heavy rain is coming, don't irrigate (risk of waterlogging)
    # ------------------------------------------------------------------
    if forecast_rain_mm >= 15.0:
        # Significant rain is coming – hold off to prevent oversaturation
        action = "HOLD_IRRIGATION"
        recommendation = (
            f"HOLD IRRIGATION. Significant rainfall ({forecast_rain_mm:.1f} mm) is forecasted within 72 hours. "
            f"Anticipated rain exceeds 3-day crop demand ({three_day_demand:.1f} mm). "
            f"Hold off to prevent waterlogging, nutrient leaching, and root hypoxia."
        )
        water_amount_mm = 0.0

    elif net_water_deficit <= 2.0:
        # Deficit is minimal – residual soil moisture or light rain is sufficient
        action = "DELAY_OR_LIGHT"
        recommendation = (
            f"DELAY OR LIGHT CYCLE. Light rain or residual soil moisture covers current demand. "
            f"Net deficit is only {net_water_deficit:.1f} mm. Monitor topsoil before irrigating."
        )
        water_amount_mm = 0.0

    elif net_water_deficit > base_dose:
        # Deficit exceeds recommended single-dose – irrigate at full rate
        action = "IRRIGATE_FULL"
        # Cap max application at 130% of soil's recommended dose to avoid runoff
        water_amount_mm = min(net_water_deficit, base_dose * 1.3)
        recommendation = (
            f"IRRIGATE. Cumulative crop evapotranspiration ({three_day_demand:.1f} mm) is outpacing rainfall. "
            f"Apply approximately {water_amount_mm:.1f} mm over {soil_info['frequency']} to replenish root zone field capacity."
        )
    else:
        # Small deficit – apply maintenance irrigation to stay at optimal moisture
        action = "IRRIGATE_MAINTENANCE"
        water_amount_mm = net_water_deficit
        recommendation = (
            f"APPLY MAINTENANCE IRRIGATION. Supply {water_amount_mm:.1f} mm to keep soil moisture within optimal tension."
        )

    # Return a structured response the AI agent can parse and explain to the farmer
    return {
        "crop": crop.capitalize(),
        "growth_stage": growth_stage,
        "soil_type": soil_type.capitalize(),
        "kc_factor": kc,                            # Crop coefficient used
        "reference_et0_mm_day": et0_mm,             # Grass reference ET0 input
        "daily_crop_water_loss_mm": daily_crop_water_loss,   # ETc = ET0 × Kc
        "three_day_crop_demand_mm": three_day_demand,        # 3-day total water need
        "forecast_rain_3d_mm": forecast_rain_mm,    # Forecasted rain over 3 days
        "net_deficit_mm": max(0.0, net_water_deficit),       # Remaining water gap (never negative)
        "action": action,                           # Decision code: HOLD/DELAY/IRRIGATE
        "recommended_dose_mm": round(water_amount_mm, 1),   # How much water to apply
        "soil_notes": soil_info["note"],            # Practical soil management advice
        "recommendation": recommendation,           # Full plain-English advisory text
        "source": "irrigation_management_guide.md"  # Citation for RAG source
    }
