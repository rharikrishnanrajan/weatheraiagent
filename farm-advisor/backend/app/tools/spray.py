# ==============================================================================
# AgriPulse: Spray Window Checker Tool
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Analyzes hourly meteorological forecasts to identify safe agrochemical spray windows.
# 2. Checks wind speed: flags thermal drift (>18 km/h) or atmospheric inversions (<3 km/h).
# 3. Evaluates rainfastness: ensures 3 hours of dry weather post-application.
# 4. Monitors temperature & humidity: prevents foliar scorching (>28°C) and droplet evaporation.
# ==============================================================================

import logging
from typing import Dict, Any, List
from langchain_core.tools import tool

logger = logging.getLogger("farm_advisor.tools.spray")


@tool
def spray_window_checker(
    forecast_hours: List[Dict[str, Any]],
    target_pesticide_type: str = "general"
) -> Dict[str, Any]:
    """Evaluate hourly weather conditions to determine safe and effective pesticide/fungicide/fertilizer spraying windows.
    
    Args:
        forecast_hours: List of hourly forecast points containing 'time', 'temperature_2m', 'relative_humidity_2m', 'precipitation', 'wind_speed_10m', 'wind_gusts_10m'.
        target_pesticide_type: Type of agrochemical ('fungicide', 'herbicide', 'insecticide', 'foliar_fertilizer', 'general').
    """
    if not forecast_hours or len(forecast_hours) == 0:
        return {
            "status": "insufficient_data",
            "message": "No hourly forecast data provided. Fetch forecast hours from weather tool first."
        }
    
    # Analyze upcoming 36 hours for field operation planning
    window_evaluations = []
    
    for idx, hour in enumerate(forecast_hours[:36]):
        t_time = hour.get("time", f"Hour+{idx}")
        temp = float(hour.get("temperature_2m", 20.0))
        hum = float(hour.get("relative_humidity_2m", 60.0))
        rain = float(hour.get("precipitation", 0.0))
        wind = float(hour.get("wind_speed_10m", 8.0))
        gusts = float(hour.get("wind_gusts_10m", wind * 1.3))
        
        reasons = []
        is_safe = True
        
        # 1. Wind evaluation: Safe window is 3 - 15 km/h
        if wind > 18.0 or gusts > 25.0:
            is_safe = False
            reasons.append(f"High wind drift risk (wind {wind:.1f} km/h, gusts {gusts:.1f} km/h)")
        elif wind < 3.0:
            reasons.append("Low wind / possible thermal inversion (droplets may hang in air)")
            
        # 2. Rain evaluation: check immediate rain and next 3 hours (rainfastness window)
        future_rain = rain
        for lookahead in range(1, 4):
            if idx + lookahead < len(forecast_hours):
                future_rain += float(forecast_hours[idx + lookahead].get("precipitation", 0.0))
                
        if rain > 0.1:
            is_safe = False
            reasons.append(f"Active rainfall ({rain:.1f} mm) causes immediate pesticide wash-off")
        elif future_rain > 1.0:
            is_safe = False
            reasons.append(f"Rain expected within 3 hours ({future_rain:.1f} mm), compromising rainfastness")
            
        # 3. Temperature evaluation: Prevent foliar phytotoxicity / burn (>28°C)
        if temp > 28.0:
            is_safe = False
            reasons.append(f"High temperature ({temp:.1f}°C) causes droplet volatilization and crop foliage scorching")
        elif temp < 5.0:
            is_safe = False
            reasons.append(f"Low temperature ({temp:.1f}°C) slows systemic absorption")
            
        # 4. Humidity evaluation: Droplet evaporation vs drying rate
        if hum < 35.0:
            reasons.append(f"Low humidity ({hum:.0f}%) accelerates droplet evaporation before target contact")
        elif hum > 88.0 and not is_safe:
            reasons.append(f"Very high humidity ({hum:.0f}%) delays drying")

        # 5. Composite safety score (0 - 100)
        score = 100
        if not is_safe:
            score = max(20, 100 - len(reasons) * 30)
        else:
            score = 100 - (len(reasons) * 15)

        rating = "Optimal" if score >= 85 else ("Moderate/Marginal" if score >= 60 else "Unsafe")
        
        window_evaluations.append({
            "time": t_time,
            "rating": rating,
            "safety_score": score,
            "is_safe": is_safe,
            "temperature_c": temp,
            "humidity_pct": hum,
            "wind_speed_kmh": wind,
            "rain_mm": rain,
            "warnings_or_factors": reasons
        })
        
    # Extract optimal spray windows
    optimal_windows = [w for w in window_evaluations if w["rating"] == "Optimal"]
    marginal_windows = [w for w in window_evaluations if w["rating"] == "Moderate/Marginal"]
    
    summary_text = ""
    if optimal_windows:
        times_str = ", ".join([w["time"][-5:] for w in optimal_windows[:4]])
        summary_text = f"Optimal spray conditions detected during hours: {times_str}. Low drift risk and dry canopy."
    elif marginal_windows:
        times_str = ", ".join([w["time"][-5:] for w in marginal_windows[:3]])
        summary_text = f"Marginal spray conditions around {times_str}. Monitor wind gusts and spray with coarse droplet nozzles."
    else:
        summary_text = "No safe spray windows in the next 36 hours due to wind or rainfall. Hold applications to avoid chemical loss."

    return {
        "target_pesticide_type": target_pesticide_type,
        "summary": summary_text,
        "safe_hours_count": len(optimal_windows),
        "marginal_hours_count": len(marginal_windows),
        "best_windows": optimal_windows[:5],
        "all_hourly_ratings": window_evaluations[:24],
        "source": "pest_and_fungal_disease_guide.md"
    }
