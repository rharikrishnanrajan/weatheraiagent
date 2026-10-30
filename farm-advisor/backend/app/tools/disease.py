import logging
from typing import Dict, Any, List
from langchain_core.tools import tool

logger = logging.getLogger("farm_advisor.tools.disease")

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
            "prevention": "Avoid planting wheat directly after maize. Apply triazole fungicide during early flowering (anthesis) if wet conditions persist."
        }
    ],
    "potato": [
        {
            "name": "Potato Late Blight (Phytophthora infestans)",
            "pathogen": "Oomycete Fungus",
            "optimal_temp_range": (12.0, 22.0),
            "min_rh": 85.0,
            "min_wetness_hours": 6.0,
            "severity_weight": 1.0,
            "symptoms": "Rapid foliar blighting, brownish rot with white mycelium in moist canopies; tuber breakdown.",
            "prevention": "Destroy cull piles; use certified seed potatoes; preventive fungicide sprays before row closure."
        }
    ],
    "rice": [
        {
            "name": "Rice Blast (Magnaporthe oryzae)",
            "pathogen": "Fungus",
            "optimal_temp_range": (24.0, 28.0),
            "min_rh": 90.0,
            "min_wetness_hours": 8.0,
            "severity_weight": 0.95,
            "symptoms": "Spindle-shaped spots with gray/white centers and brown margins on leaves; neck rot at heading.",
            "prevention": "Avoid excessive nitrogen fertilizers; maintain proper flood levels; use tricyclazole or isoprothiolane preventatively."
        }
    ]
}

DEFAULT_DISEASE_MODEL = [
    {
        "name": "Foliar Fungal Infection (General Mildew / Leaf Spot)",
        "pathogen": "Fungus",
        "optimal_temp_range": (18.0, 28.0),
        "min_rh": 80.0,
        "min_wetness_hours": 5.0,
        "severity_weight": 0.7,
        "symptoms": "Foliar discoloration, powdery or moldy patches, chlorotic lesions.",
        "prevention": "Improve airflow through weeding and plant spacing; avoid wetting leaves during irrigation."
    }
]

@tool
def disease_risk_estimator(
    crop: str,
    temp_c: float,
    humidity_pct: float,
    leaf_wetness_hours: float
) -> Dict[str, Any]:
    """Estimate agronomic plant disease and pest risks based on temperature, relative humidity, and canopy leaf wetness duration.
    
    Args:
        crop: Crop name (e.g. 'Tomato', 'Corn', 'Wheat', 'Potato', 'Rice').
        temp_c: Current or average 24h temperature in degrees Celsius.
        humidity_pct: Relative humidity percentage (0-100%).
        leaf_wetness_hours: Number of hours leaves remain wet from rain, dew, or fog.
    """
    crop_lower = crop.lower().strip()
    models = DISEASE_MODELS.get(crop_lower, DEFAULT_DISEASE_MODEL)
    
    findings = []
    max_risk_score = 0.0
    
    for m in models:
        t_min, t_max = m["optimal_temp_range"]
        
        # Temp factor: 1.0 if inside optimal range, decays outside
        if t_min <= temp_c <= t_max:
            temp_score = 1.0
        elif temp_c < t_min:
            temp_score = max(0.0, 1.0 - (t_min - temp_c) / 6.0)
        else:
            temp_score = max(0.0, 1.0 - (temp_c - t_max) / 6.0)
            
        # Humidity factor
        rh_threshold = m["min_rh"]
        if humidity_pct >= rh_threshold:
            rh_score = 1.0
        else:
            rh_score = max(0.0, 1.0 - (rh_threshold - humidity_pct) / 25.0)
            
        # Wetness factor
        wet_threshold = m["min_wetness_hours"]
        if leaf_wetness_hours >= wet_threshold:
            wet_score = 1.0
        else:
            wet_score = max(0.0, leaf_wetness_hours / wet_threshold)
            
        # Composite pathogen development index
        risk_index = (temp_score * 0.35 + rh_score * 0.35 + wet_score * 0.30) * m["severity_weight"]
        risk_score = round(risk_index * 100, 1)
        
        if risk_score > max_risk_score:
            max_risk_score = risk_score
            
        if risk_score >= 70.0:
            level = "High / Outbreak Alert"
        elif risk_score >= 45.0:
            level = "Moderate"
        else:
            level = "Low"
            
        findings.append({
            "disease_name": m["name"],
            "pathogen_type": m["pathogen"],
            "calculated_risk_index": risk_score,
            "risk_level": level,
            "symptoms_to_scout": m["symptoms"],
            "preventive_management": m["prevention"]
        })

    if max_risk_score >= 70.0:
        overall_status = "CRITICAL / HIGH RISK"
        summary = f"Favorable environmental conditions detected for fungal/bacterial spread on {crop}. Immediate field scouting and preventative measures advised."
    elif max_risk_score >= 45.0:
        overall_status = "MODERATE RISK"
        summary = f"Conditions moderately support pathogen sporulation. Monitor weather updates and inspect bottom canopy foliage."
    else:
        overall_status = "LOW RISK"
        summary = f"Current temperature ({temp_c}°C) and moisture levels do not indicate imminent disease pressure for {crop}."

    return {
        "crop": crop,
        "overall_status": overall_status,
        "peak_risk_score": max_risk_score,
        "assessed_temp_c": temp_c,
        "assessed_humidity_pct": humidity_pct,
        "assessed_leaf_wetness_hours": leaf_wetness_hours,
        "summary": summary,
        "disease_threats": findings
    }
