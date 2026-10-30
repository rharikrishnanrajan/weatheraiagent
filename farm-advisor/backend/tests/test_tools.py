import pytest
from app.tools.irrigation import irrigation_advisor
from app.tools.spray import spray_window_checker
from app.tools.disease import disease_risk_estimator
from app.tools.weather import detect_weather_hazards

def test_irrigation_advisor_hold_on_heavy_rain():
    # If 25 mm rain is forecasted, irrigation must be placed on hold
    result = irrigation_advisor.invoke({
        "crop": "Tomato",
        "growth_stage": "flowering",
        "soil_type": "Loamy",
        "forecast_rain_mm": 25.0,
        "et0_mm": 4.5,
        "recent_rain_mm": 5.0
    })
    assert result["action"] == "HOLD IRRIGATION"
    assert result["suggested_application_depth_mm"] == 0.0
    assert "25" in result["explanation"]

def test_irrigation_advisor_recommends_irrigation_in_dry_conditions():
    # In dry weather (0 mm rain) during flowering stage, irrigation should be recommended
    result = irrigation_advisor.invoke({
        "crop": "Tomato",
        "growth_stage": "flowering",
        "soil_type": "Loamy",
        "forecast_rain_mm": 0.0,
        "et0_mm": 5.0,
        "recent_rain_mm": 0.0
    })
    assert result["action"] == "IRRIGATE"
    assert result["suggested_application_depth_mm"] > 0
    assert result["water_volume_m3_per_hectare"] > 0
    assert "Early morning" in result["best_timing"]

def test_spray_window_checker_flags_high_winds():
    # Wind speed > 18 km/h or gusts > 25 km/h must be marked unsafe
    sample_hours = [
        {
            "time": "2026-10-30T10:00",
            "temperature_2m": 22.0,
            "relative_humidity_2m": 55.0,
            "precipitation": 0.0,
            "wind_speed_10m": 24.0,
            "wind_gusts_10m": 35.0
        }
    ]
    result = spray_window_checker.invoke({
        "forecast_hours": sample_hours,
        "target_pesticide_type": "fungicide"
    })
    assert result["verdict"] == "DELAY"
    assert "NO SAFE SPRAY WINDOW" in result["recommendation"]
    assert any("drift risk" in flag for flag in result["evaluated_hours_sample"][0]["flags"])

def test_spray_window_checker_approves_calm_conditions():
    # Calm wind (8 km/h), moderate temp (20 C), no rain
    sample_hours = [
        {
            "time": f"2026-10-30T{h:02d}:00",
            "temperature_2m": 20.0,
            "relative_humidity_2m": 60.0,
            "precipitation": 0.0,
            "wind_speed_10m": 8.0,
            "wind_gusts_10m": 10.0
        } for h in range(8, 14)
    ]
    result = spray_window_checker.invoke({
        "forecast_hours": sample_hours,
        "target_pesticide_type": "insecticide"
    })
    assert result["verdict"] == "APPROVED"
    assert result["optimal_window_start"] != "None"

def test_disease_risk_estimator_high_humidity_blight():
    # Cool temperatures (18 C), 92% humidity, 8 hours leaf wetness should trigger late blight alert
    result = disease_risk_estimator.invoke({
        "crop": "Tomato",
        "temp_c": 18.0,
        "humidity_pct": 92.0,
        "leaf_wetness_hours": 8.0
    })
    assert "HIGH RISK" in result["overall_status"] or "CRITICAL" in result["overall_status"]
    assert result["peak_risk_score"] >= 70.0
    threat_names = [t["disease_name"] for t in result["disease_threats"]]
    assert any("Late Blight" in name for name in threat_names)

def test_detect_weather_hazards_frost_and_heat():
    raw_mock = {
        "daily": {
            "time": ["2026-11-01", "2026-11-02"],
            "temperature_2m_min": [-2.0, 15.0],
            "temperature_2m_max": [10.0, 40.0],
            "precipitation_sum": [0.0, 40.0],
            "wind_speed_10m_max": [12.0, 20.0]
        },
        "hourly": {
            "relative_humidity_2m": [60] * 48
        }
    }
    alerts = detect_weather_hazards(raw_mock)
    categories = [a["category"] for a in alerts]
    assert "Frost" in categories
    assert "Heatwave" in categories
    assert "Heavy Rain" in categories
