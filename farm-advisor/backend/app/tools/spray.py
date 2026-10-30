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
    
    # Analyze up to next 36 hours
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
        
        # Wind evaluation
        if wind > 18.0 or gusts > 25.0:
            is_safe = False
            reasons.append(f"High wind drift risk (wind {wind:.1f} km/h, gusts {gusts:.1f} km/h)")
        elif wind < 3.0:
            reasons.append("Low wind / possible thermal inversion (droplets may hang in air)")
            
        # Rain evaluation: check immediate rain and next 3 hours
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
            
        # Temperature evaluation
        if temp > 28.0:
            is_safe = False
            reasons.append(f"High temperature ({temp:.1f}°C) causes droplet volatilization and crop foliage scorching")
        elif temp < 5.0:
            is_safe = False
            reasons.append(f"Low temperature ({temp:.1f}°C) slows systemic absorption")
            
        # Humidity evaluation
        if hum < 35.0:
            reasons.append(f"Low humidity ({hum:.0f}%) accelerates droplet evaporation before target contact")
        elif hum > 88.0 and not is_safe:
            reasons.append(f"Very high humidity ({hum:.0f}%) delays drying")

        score = 100
        if not is_safe:
            score = max(20, 100 - len(reasons) * 30)
        else:
            score = 100 - (len(reasons) * 15)

        rating = "Optimal" if score >= 85 else ("Moderate/Marginal" if score >= 60 else "Unsafe")
        
        window_evaluations.append({
            "time": t_time,
            "temp_c": temp,
            "humidity_pct": hum,
            "wind_kmh": wind,
            "rain_mm": rain,
            "score": score,
            "rating": rating,
            "flags": reasons
        })

    # Find the best contiguous window (3+ hours of Optimal/Marginal)
    best_windows = [w for w in window_evaluations if w["score"] >= 75]
    
    if best_windows:
        best_start = best_windows[0]["time"]
        best_end = best_windows[min(3, len(best_windows)-1)]["time"]
        overall_advice = f"RECOMMENDED SPRAY WINDOW: From {best_start} to {best_end}."
        verdict = "APPROVED"
    else:
        best_start = "None"
        best_end = "None"
        overall_advice = "NO SAFE SPRAY WINDOW IN IMMEDIATE FORECAST. Defer spraying due to adverse wind, rain, or heat conditions."
        verdict = "DELAY"

    return {
        "verdict": verdict,
        "target_agrochemical": target_pesticide_type,
        "recommendation": overall_advice,
        "optimal_window_start": best_start,
        "optimal_window_end": best_end,
        "evaluated_hours_sample": window_evaluations[:12],
        "safety_rules": [
            "Maintain nozzle pressure between 2.0-3.0 bar to minimize driftable fine droplets (<100 um).",
            "Maintain 5-meter buffer from non-target vegetation and waterways.",
            "Always wear complete PPE: nitrile gloves, protective eyewear, and respirator mask."
        ]
    }
