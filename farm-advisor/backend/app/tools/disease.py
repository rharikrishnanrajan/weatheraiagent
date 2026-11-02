# ==============================================================================
# AgriPulse: Disease & Pest Risk Estimator Tool
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Models pathogen biology (Late Blight, Powdery Mildew, Rust, Leaf Spot).
# 2. Scans hourly weather data for favorable spore germination conditions
#    (prolonged leaf wetness, high relative humidity, optimal incubation temperatures).
# 3. Outputs risk score (0-100), severity tier (LOW, MODERATE, HIGH, CRITICAL),
#    visible diagnostic symptoms, and practical prevention steps.
# ==============================================================================

import logging
from typing import Dict, Any, List
from langchain_core.tools import tool

logger = logging.getLogger("farm_advisor.tools.disease")

# Biological environmental parameters for common crop pathogens
DISEASE_MODELS = {
    "tomato": [
        {
            "name": "Late Blight (Phytophthora infestans)",
            "pathogen": "Oomycete Fungus",
            "optimal_temp_range": (12.0, 22.0),
            "min_rh": 85.0,
            "min_wetness_hours": 6.0,
            "severity_weight": 1.0,
            "symptoms": "Water-soaked dark lesions on leaves/stems with white fuzzy sporulation on leaf undersides in humid conditions.",
            "prevention": "Ensure good spacing; avoid overhead irrigation. Apply copper hydroxide or bio-fungicide (Bacillus subtilis) preventively before rain events."
        },
        {
            "name": "Early Blight (Alternaria solani)",
            "pathogen": "Fungus",
            "optimal_temp_range": (20.0, 29.0),
            "min_rh": 75.0,
            "min_wetness_hours": 4.0,
            "severity_weight": 0.8,
            "symptoms": "Concentric ring 'target' spots with yellow halos on older bottom leaves.",
            "prevention": "Mulch beds to stop spore splash from soil; prune lower yellowed foliage; rotate solanaceous crops."
        },
        {
            "name": "Bacterial Spot (Xanthomonas)",
            "pathogen": "Bacteria",
            "optimal_temp_range": (24.0, 30.0),
            "min_rh": 80.0,
            "min_wetness_hours": 5.0,
            "severity_weight": 0.75,
            "symptoms": "Small greasy water-soaked circular leaf spots that turn brown/black.",
            "prevention": "Do not work in wet fields. Use certified disease-free seeds; copper sprays with mancozeb tank mix if permitted."
        }
    ],
    "corn": [
        {
            "name": "Northern Corn Leaf Blight (Exserohilum turcicum)",
            "pathogen": "Fungus",
            "optimal_temp_range": (18.0, 27.0),
            "min_rh": 80.0,
            "min_wetness_hours": 6.0,
            "severity_weight": 0.85,
            "symptoms": "Long, elliptical cigar-shaped grayish-green to tan lesions.",
            "prevention": "Plant resistant hybrids; incorporate crop debris after harvest; fungicide application if lesions reach ear leaf before tassel."
        },
        {
            "name": "Gray Leaf Spot (Cercospora zeae-maydis)",
            "pathogen": "Fungus",
            "optimal_temp_range": (25.0, 32.0),
            "min_rh": 88.0,
            "min_wetness_hours": 8.0,
            "severity_weight": 0.9,
            "symptoms": "Rectangular, blocky lesions restricted between leaf veins.",
            "prevention": "Crop rotation with non-host (soybeans); select hybrids with high tolerance scores."
        }
    ],
    "wheat": [
        {
            "name": "Stripe / Yellow Rust (Puccinia striiformis)",
            "pathogen": "Fungus",
            "optimal_temp_range": (10.0, 16.0),
            "min_rh": 80.0,
            "min_wetness_hours": 4.0,
            "severity_weight": 0.95,
            "symptoms": "Yellowish-orange pustules arranged in narrow linear stripes on leaf surfaces.",
            "prevention": "Sow resistant cultivars. Timely triazole fungicide spray at first sign of pustules on flag leaf."
        },
        {
            "name": "Fusarium Head Blight / Scab",
            "pathogen": "Fungus",
            "optimal_temp_range": (22.0, 29.0),
            "min_rh": 85.0,
            "min_wetness_hours": 12.0,
            "severity_weight": 1.0,
            "symptoms": "Bleached spikelets on heads during flowering, pinkish spore masses at spikelet base.",
            "prevention": "Avoid following corn with wheat; apply targeted fungicide (e.g. prothioconazole) at early anthesis."
        }
    ],
    "potato": [
        {
            "name": "Potato Late Blight",
            "pathogen": "Oomycete Fungus",
            "optimal_temp_range": (10.0, 21.0),
            "min_rh": 90.0,
            "min_wetness_hours": 6.0,
            "severity_weight": 1.0,
            "symptoms": "Irregular brownish lesions with pale halos; decaying tubers smell pungent.",
            "prevention": "Destroy cull piles; apply systemic/protectant fungicides on Smith Period alert."
        }
    ]
}

# Fallback generic foliar disease model for unspecified crops
GENERIC_DISEASE_MODELS = [
    {
        "name": "Foliar Fungal Leaf Spot / Blight Complex",
        "pathogen": "Fungal Spores",
        "optimal_temp_range": (18.0, 28.0),
        "min_rh": 80.0,
        "min_wetness_hours": 6.0,
        "severity_weight": 0.8,
        "symptoms": "Dark brown or necrotic spots on leaf foliage, chlorosis, and premature leaf drop.",
        "prevention": "Improve airflow, avoid late evening overhead irrigation, apply bio-fungicide preventatively."
    },
    {
        "name": "Powdery Mildew",
        "pathogen": "Fungus",
        "optimal_temp_range": (15.0, 26.0),
        "min_rh": 65.0,
        "min_wetness_hours": 2.0,
        "severity_weight": 0.6,
        "symptoms": "White talcum powder-like fungal patches on upper leaf surfaces and young shoots.",
        "prevention": "Apply wettable sulfur or potassium bicarbonate at first sign of colonies."
    }
]


@tool
def disease_risk_estimator(
    crop: str,
    forecast_hours: List[Dict[str, Any]],
    current_humidity_pct: float = 65.0
) -> Dict[str, Any]:
    """Estimate fungal and pest pathogen outbreak risk based on weather forecast conditions.
    
    Args:
        crop: Crop name (e.g., 'Tomato', 'Corn', 'Wheat', 'Potato').
        forecast_hours: List of hourly forecast dicts with 'temperature_2m', 'relative_humidity_2m', 'precipitation'.
        current_humidity_pct: Current relative humidity percentage.
    """
    crop_lower = crop.lower().strip()
    models = DISEASE_MODELS.get(crop_lower, GENERIC_DISEASE_MODELS)
    
    # Calculate environmental statistics over next 48 hours
    analyzed_hours = forecast_hours[:48] if forecast_hours else []
    
    if not analyzed_hours:
        # Fallback evaluation based on current conditions
        temp = 20.0
        humidity = current_humidity_pct
        rain_hours = 0
        consecutive_wet_hours = 0
    else:
        temps = [float(h.get("temperature_2m", 20.0)) for h in analyzed_hours]
        humids = [float(h.get("relative_humidity_2m", 60.0)) for h in analyzed_hours]
        rains = [float(h.get("precipitation", 0.0)) for h in analyzed_hours]
        
        avg_temp = sum(temps) / len(temps)
        avg_humid = sum(humids) / len(humids)
        rain_hours = sum(1 for r in rains if r > 0.1)
        
        # Estimate leaf wetness duration: hours where rain > 0 or RH > 88%
        wet_hours = sum(1 for h in analyzed_hours if float(h.get("precipitation", 0.0)) > 0.05 or float(h.get("relative_humidity_2m", 0.0)) >= 88.0)
        
        # Calculate max consecutive humid/wet hours
        consecutive_wet_hours = 0
        current_run = 0
        for h in analyzed_hours:
            if float(h.get("precipitation", 0.0)) > 0.05 or float(h.get("relative_humidity_2m", 0.0)) >= 85.0:
                current_run += 1
                consecutive_wet_hours = max(consecutive_wet_hours, current_run)
            else:
                current_run = 0

    evaluated_diseases = []
    max_risk_score = 0
    
    for dis in models:
        min_temp, max_temp = dis["optimal_temp_range"]
        target_rh = dis["min_rh"]
        target_wet = dis["min_wetness_hours"]
        
        # Temperature suitability factor (0.0 to 1.0)
        temp_factor = 0.0
        if analyzed_hours:
            favorable_temp_hours = sum(1 for t in temps if min_temp <= t <= max_temp)
            temp_factor = min(1.0, favorable_temp_hours / 24.0)
        else:
            temp_factor = 0.5
            
        # Humidity suitability factor (0.0 to 1.0)
        humid_factor = 0.0
        if analyzed_hours:
            favorable_humid_hours = sum(1 for h in humids if h >= target_rh)
            humid_factor = min(1.0, favorable_humid_hours / 18.0)
        else:
            humid_factor = 0.6 if current_humidity_pct >= target_rh else 0.2
            
        # Leaf wetness duration factor (0.0 to 1.0)
        wet_factor = min(1.0, consecutive_wet_hours / max(1.0, target_wet))
        
        # Calculate composite pathogen development score (0 - 100)
        raw_score = (temp_factor * 0.35 + humid_factor * 0.35 + wet_factor * 0.30) * 100 * dis["severity_weight"]
        score = min(100, max(5, int(raw_score)))
        
        risk_level = "LOW"
        if score >= 75:
            risk_level = "HIGH / CRITICAL"
        elif score >= 50:
            risk_level = "MODERATE"
        elif score >= 30:
            risk_level = "GUARDED"
            
        max_risk_score = max(max_risk_score, score)
        
        evaluated_diseases.append({
            "disease_name": dis["name"],
            "pathogen_type": dis["pathogen"],
            "risk_score": score,
            "risk_level": risk_level,
            "symptoms": dis["symptoms"],
            "prevention_strategy": dis["prevention"]
        })
        
    evaluated_diseases.sort(key=lambda x: x["risk_score"], reverse=True)
    top_disease = evaluated_diseases[0] if evaluated_diseases else None
    
    overall_level = "LOW"
    if max_risk_score >= 75:
        overall_level = "HIGH / CRITICAL"
    elif max_risk_score >= 50:
        overall_level = "MODERATE"
    elif max_risk_score >= 30:
        overall_level = "GUARDED"

    summary = (
        f"Overall pathogen risk for {crop.capitalize()} is rated {overall_level} (Score {max_risk_score}/100). "
        f"Primary threat to monitor: {top_disease['disease_name']} ({top_disease['risk_level']})."
        if top_disease else "Pathogen risk is minimal under forecasted dry conditions."
    )

    return {
        "crop": crop.capitalize(),
        "overall_risk_level": overall_level,
        "overall_risk_score": max_risk_score,
        "summary": summary,
        "consecutive_wet_hours": consecutive_wet_hours,
        "rain_hours_next_48h": rain_hours if analyzed_hours else 0,
        "diseases": evaluated_diseases,
        "source": "pest_and_fungal_disease_guide.md"
    }
