# ==============================================================================
# AgriPulse: Spray Window Checker Tool
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Analyzes hourly meteorological forecasts to identify safe agrochemical spray windows.
# 2. Checks wind speed: flags thermal drift (>18 km/h) or atmospheric inversions (<3 km/h).
# 3. Evaluates rainfastness: ensures 3 hours of dry weather post-application.
# 4. Monitors temperature & humidity: prevents foliar scorching (>28°C) and droplet evaporation.
#
# BEGINNER TIP: "Spray window" means the hours in the day when weather conditions are
# safe to spray pesticides, herbicides, or foliar fertilizers without the chemical being
# blown away (drift), washed off by rain, or scorching the crop in high heat.
# ==============================================================================

import logging
from typing import Dict, Any, List
from langchain_core.tools import tool

logger = logging.getLogger("farm_advisor.tools.spray")


# ==============================================================================
# AGENT TOOL: spray_window_checker
# ==============================================================================
@tool
def spray_window_checker(
    forecast_hours: List[Dict[str, Any]],
    target_pesticide_type: str = "general"
) -> Dict[str, Any]:
    """Evaluate hourly weather conditions to determine safe and effective pesticide/fungicide/fertilizer spraying windows.

    Args:
        forecast_hours: List of hourly forecast points containing
            'time', 'temperature_2m', 'relative_humidity_2m',
            'precipitation', 'wind_speed_10m', 'wind_gusts_10m'.
        target_pesticide_type: Type of agrochemical
            ('fungicide', 'herbicide', 'insecticide', 'foliar_fertilizer', 'general').
    """
    # Guard: require at least one hour of forecast data
    if not forecast_hours or len(forecast_hours) == 0:
        return {
            "status": "insufficient_data",
            "message": "No hourly forecast data provided. Fetch forecast hours from weather tool first."
        }

    # We will analyze the next 36 hours for spray planning
    window_evaluations = []

    for idx, hour in enumerate(forecast_hours[:36]):
        # Extract meteorological values for this specific hour
        t_time = hour.get("time", f"Hour+{idx}")
        temp = float(hour.get("temperature_2m", 20.0))             # Air temperature (°C)
        hum = float(hour.get("relative_humidity_2m", 60.0))        # Relative humidity (%)
        rain = float(hour.get("precipitation", 0.0))               # Rainfall this hour (mm)
        wind = float(hour.get("wind_speed_10m", 8.0))              # Wind speed (km/h)
        gusts = float(hour.get("wind_gusts_10m", wind * 1.3))      # Gust speed (km/h)

        reasons = []    # List of warning reasons for this hour
        is_safe = True  # Start with "safe" and apply disqualifiers

        # ------------------------------------------------------------------
        # CHECK 1: WIND SPEED
        # Safe spray range: 3 to 15 km/h
        # - Below 3 km/h: thermal inversion risk (droplets drift back down unpredictably)
        # - Above 18 km/h: spray drift – chemical blows off-target onto neighbouring fields
        # ------------------------------------------------------------------
        if wind > 18.0 or gusts > 25.0:
            is_safe = False
            reasons.append(f"High wind drift risk (wind {wind:.1f} km/h, gusts {gusts:.1f} km/h)")
        elif wind < 3.0:
            # This is a soft warning – not an outright disqualifier
            reasons.append("Low wind / possible thermal inversion (droplets may hang in air)")

        # ------------------------------------------------------------------
        # CHECK 2: RAINFALL & RAINFASTNESS
        # "Rainfastness" = minimum time needed after spraying before rain washes the chemical off.
        # Most contact pesticides need 3 dry hours post-application.
        # ------------------------------------------------------------------
        # Look ahead 3 hours to check if rain is coming soon
        future_rain = rain
        for lookahead in range(1, 4):   # Check next 3 hourly steps
            if idx + lookahead < len(forecast_hours):
                future_rain += float(forecast_hours[idx + lookahead].get("precipitation", 0.0))

        if rain > 0.1:
            # Active rain right now – immediate wash-off
            is_safe = False
            reasons.append(f"Active rainfall ({rain:.1f} mm) causes immediate pesticide wash-off")
        elif future_rain > 1.0:
            # Rain is coming within 3 hours – rainfastness window not achievable
            is_safe = False
            reasons.append(f"Rain expected within 3 hours ({future_rain:.1f} mm), compromising rainfastness")

        # ------------------------------------------------------------------
        # CHECK 3: TEMPERATURE
        # - Above 28°C: droplets evaporate before hitting leaf surface + crop scorching risk
        # - Below 5°C: systemic absorption through plant cuticle becomes too slow to be effective
        # ------------------------------------------------------------------
        if temp > 28.0:
            is_safe = False
            reasons.append(f"High temperature ({temp:.1f}°C) causes droplet volatilization and crop foliage scorching")
        elif temp < 5.0:
            is_safe = False
            reasons.append(f"Low temperature ({temp:.1f}°C) slows systemic absorption")

        # ------------------------------------------------------------------
        # CHECK 4: RELATIVE HUMIDITY
        # - Below 35%: droplets evaporate before contacting leaf surface (small-droplet nozzles at risk)
        # - Above 88%: wet canopy delays drying; fungal spread risk if spraying fungicides
        # These are advisory notes, not hard disqualifiers
        # ------------------------------------------------------------------
        if hum < 35.0:
            reasons.append(f"Low humidity ({hum:.0f}%) accelerates droplet evaporation before target contact")
        elif hum > 88.0 and not is_safe:
            reasons.append(f"Very high humidity ({hum:.0f}%) delays drying")

        # ------------------------------------------------------------------
        # COMPOSITE SAFETY SCORE (0 – 100)
        # Perfect conditions = 100. Each problem reduces the score.
        # ------------------------------------------------------------------
        score = 100
        if not is_safe:
            # Major disqualifiers: each reason docks 30 points
            score = max(20, 100 - len(reasons) * 30)
        else:
            # Minor advisories: each note docks 15 points
            score = 100 - (len(reasons) * 15)

        # Convert score to a plain-language rating
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
            "warnings_or_factors": reasons  # Human-readable reasons for this hour's score
        })

    # ------------------------------------------------------------------
    # SUMMARIZE: Find the best windows across the 36-hour period
    # ------------------------------------------------------------------
    optimal_windows = [w for w in window_evaluations if w["rating"] == "Optimal"]
    marginal_windows = [w for w in window_evaluations if w["rating"] == "Moderate/Marginal"]

    # Build a one-sentence summary for the farmer
    summary_text = ""
    if optimal_windows:
        # Show the earliest optimal hours (last 5 chars of ISO time = "HH:MM")
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
        "safe_hours_count": len(optimal_windows),       # How many optimal hours found
        "marginal_hours_count": len(marginal_windows),  # How many marginal hours found
        "best_windows": optimal_windows[:5],            # Top 5 safest spray hours
        "all_hourly_ratings": window_evaluations[:24],  # Full 24-hour evaluation table
        "source": "pest_and_fungal_disease_guide.md"
    }
