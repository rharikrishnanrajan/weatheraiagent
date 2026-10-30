# AgriPulse: Weather-Based Farming Advisory AI Agent

**AgriPulse** is a production-grade, full-stack AI agronomic advisor that empowers farmers and agronomists to make climate-smart, timely, and profitable decisions. It seamlessly fuses live meteorological forecasts from [Open-Meteo](https://open-meteo.com/), an agricultural extension knowledge base (RAG via persistent Chroma), and multi-turn conversational farm memory (LangGraph + SQLite) with neural reasoning via **NVIDIA AI Endpoints (NVIDIA NIM)**.

---

## Architecture Overview

```text
farm-advisor/
├── backend/
│   ├── app/
│   │   ├── main.py                         # FastAPI core with CORS, structured logging, NIM error handling
│   │   ├── config.py                       # Pydantic Settings with NVIDIA & path configuration
│   │   ├── api/                            # REST and SSE API endpoints
│   │   │   ├── chat.py                     # POST /api/chat with Server-Sent Events (SSE) token & tool streaming
│   │   │   ├── profile.py                  # GET/PUT /api/profile for farm characteristics
│   │   │   ├── threads.py                  # GET/DELETE /api/threads conversation management
│   │   │   ├── weather.py                  # GET /api/weather with geocoding, current, 7-day & alerts
│   │   │   └── kb.py                       # GET/POST /api/kb for document ingestion & semantic search
│   │   ├── agent/                          # LangGraph ReAct agent & memory
│   │   │   ├── agent.py                    # Compiled LangGraph workflow, streaming & citation logic
│   │   │   ├── prompts.py                  # Practical agronomy persona system prompt
│   │   │   ├── memory.py                   # AsyncSqliteSaver checkpointing & token-length trimming
│   │   │   └── llm.py                      # ChatNVIDIA initialization, startup tool validation & fallback
│   │   ├── tools/                          # Pydantic-typed agronomic & meteorological tools
│   │   │   ├── weather.py                  # get_weather_forecast, get_weather_alerts
│   │   │   ├── geocode.py                  # geocode_location (Open-Meteo geocoding)
│   │   │   ├── irrigation.py               # irrigation_advisor (FAO-56 evapotranspiration & soil holding)
│   │   │   ├── spray.py                    # spray_window_checker (thermal drift & rainfastness)
│   │   │   ├── disease.py                  # disease_risk_estimator (pathogen development index)
│   │   │   ├── profile.py                  # get_farm_profile, update_farm_profile
│   │   │   └── rag.py                      # search_farming_knowledge
│   │   ├── rag/                            # RAG pipeline with Chroma vector store
│   │   │   ├── ingest.py                   # Markdown/PDF/TXT parser, chunking, and batch vectorization
│   │   │   ├── retriever.py                # Semantic retrieval with optional NVIDIARerank
│   │   │   └── vectorstore.py              # NVIDIAEmbeddings with deterministic offline fallback
│   │   ├── db/                             # SQLite persistent store
│   │   │   └── session.py                  # Profiles, threads, and chat message storage
│   │   └── schemas/                        # Pydantic v2 schemas
│   │       ├── chat.py
│   │       ├── profile.py
│   │       ├── weather.py
│   │       └── kb.py
│   ├── data/
│   │   ├── knowledge_base/                 # Curated agronomy guides (irrigation, disease, sowing, fertilizer, frost)
│   │   ├── chroma_db/                      # Persistent local Chroma vectors
│   │   └── farm_advisor.db                 # SQLite database for profiles & threads
│   ├── scripts/
│   │   └── ingest.py                       # Standalone ingestion runner
│   ├── tests/
│   │   ├── test_tools.py                   # Deterministic unit tests (irrigation, spray, disease, hazards)
│   │   └── test_api_integration.py         # End-to-end FastAPI tests with mocked LLM
│   ├── requirements.txt
│   └── .env.example
├── frontend/                               # Vite + React 19 + TypeScript + Tailwind CSS
│   └── src/
│       ├── api/                            # Fetch clients & SSE streaming reader
│       ├── store/                          # Zustand state manager (profile, weather, threads, stream)
│       ├── components/                     # Navbar, WeatherCard, AlertBanner, TempPrecipChart, ToolChips
│       ├── pages/                          # ChatPage, WeatherPage, ProfilePage, KnowledgeBasePage
│       └── types/                          # TypeScript interfaces
└── README.md
```

---

## 1. NVIDIA AI Endpoints (NVIDIA NIM) Setup

AgriPulse utilizes NVIDIA NIM microservices via the `langchain-nvidia-ai-endpoints` package:
- **Chat Model**: `meta/llama-3.3-70b-instruct` (high-precision agronomic reasoning)
- **Embeddings Model**: `nvidia/llama-3.2-nv-embedqa-1b-v2` (dense vector embeddings)
- **Reranker (Optional)**: `nvidia/llama-3.2-nv-rerankqa-1b-v2` (cross-encoder relevance ranking)

### Step 1: Obtain your NVIDIA API Key
1. Visit [build.nvidia.com](https://build.nvidia.com/).
2. Sign in or create a free developer account.
3. Browse to the **meta/llama-3.3-70b-instruct** model page.
4. Click **Get API Key** and generate an API key starting with `nvapi-...`.

### Step 2: Configure Environment Variables
Copy `backend/.env.example` to `backend/.env` and insert your API key:

```env
# NVIDIA AI Endpoints Configuration
NVIDIA_API_KEY=nvapi-your-key-here
NVIDIA_CHAT_MODEL=meta/llama-3.3-70b-instruct
NVIDIA_EMBED_MODEL=nvidia/llama-3.2-nv-embedqa-1b-v2
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# Optional Reranking
USE_RERANKER=false
NVIDIA_RERANK_MODEL=nvidia/llama-3.2-nv-rerankqa-1b-v2

# Storage & Database
SQLITE_DB_PATH=./data/farm_advisor.db
CHROMA_DB_DIR=./data/chroma_db
KNOWLEDGE_BASE_DIR=./data/knowledge_base

# Server Config
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

> **Offline/Fallback Capability**: If `NVIDIA_API_KEY` is omitted, AgriPulse automatically activates its deterministic agronomy heuristic engine so that all endpoints, tools, and UI components remain completely operable.

---

## 2. Running the Backend

### Prerequisites
- Python 3.11+
- Virtual environment (`venv`)

### Installation & Execution
```bash
# Navigate to backend directory
cd farm-advisor/backend

# Activate your virtual environment (Windows PowerShell)
.venv\Scripts\Activate.ps1
# (Or on Linux/macOS: source .venv/bin/activate)

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Ingest Knowledge Base into Chroma vector database
python scripts/ingest.py

# Start FastAPI server via Uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will start at:
- **API Server**: `http://localhost:8000`
- **Swagger Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/health`

---

## 3. Running the Frontend

### Prerequisites
- Node.js 18+
- npm

### Installation & Execution
```bash
# Navigate to frontend directory
cd farm-advisor/frontend

# Install node dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend will start at:
- **Web UI**: `http://localhost:5173`

The Vite dev server automatically proxies `/api` calls to `http://127.0.0.1:8000`.

---

## 4. Running Backend Unit & Integration Tests

The test suite validates deterministic tools (FAO-56 irrigation calculations, spray windows, hazard detection, disease scoring) and FastAPI endpoints with a mocked LLM.

```bash
cd farm-advisor/backend
python -m pytest tests -v
```

All 12 tests will execute and pass:
- `test_health_check_endpoint`: Health probe and NVIDIA status check.
- `test_profile_read_and_update`: Farm profile read and persistent write.
- `test_weather_endpoint_with_location`: Live Open-Meteo forecast retrieval.
- `test_knowledge_base_search_endpoint`: Semantic Chroma vector search.
- `test_chat_endpoint_mocked_llm`: Agent ReAct execution with mocked ChatModel.
- `test_threads_list_and_messages`: Conversation persistence.
- `test_irrigation_advisor_hold_on_heavy_rain`: Verifies rain threshold pauses watering.
- `test_irrigation_advisor_recommends_irrigation_in_dry_conditions`: Calculates crop evapotranspiration.
- `test_spray_window_checker_flags_high_winds`: Verifies spray drift safety constraints.
- `test_spray_window_checker_approves_calm_conditions`: Identifies optimal application windows.
- `test_disease_risk_estimator_high_humidity_blight`: Tests Smith Periods / late blight pathogen index.
- `test_detect_weather_hazards_frost_and_heat`: Tests freeze and heatwave warnings.

---

## 5. 10 Sample Testing Queries

Use these prompts in the Web Chat interface (`http://localhost:5173`) or via `curl` to test the full range of advisory agent features:

### Query 1: Irrigation Scheduling & Soil Moisture
> *"I have flowering tomatoes in loamy soil. Based on the 3-day rainfall forecast and evapotranspiration, should I turn on my drip system tomorrow, and how much water should I apply?"*
- **Tools Triggered**: `get_weather_forecast`, `irrigation_advisor`, `search_farming_knowledge`
- **Expected Outcome**: Computes ETc, checks forecasted precipitation, recommends watering depth in mm and m³/ha, advises early morning drip timing, and cites `irrigation_management_guide.md`.

### Query 2: Chemical Spray Window Evaluation
> *"Can I spray fungicide on my corn crop this afternoon, or will the wind and rain wash it off?"*
- **Tools Triggered**: `get_weather_forecast`, `spray_window_checker`
- **Expected Outcome**: Evaluates hourly wind speed, wind gusts, temperature, and rainfastness. Flags unsafe midday heat or high winds, identifies approved calm windows, and reminds of PPE and buffer zones.

### Query 3: Frost & Freeze Hazard Protection
> *"Is there any freeze or frost hazard predicted for my farm this week, and how should I protect my young seedlings?"*
- **Tools Triggered**: `get_weather_alerts`, `get_weather_forecast`, `search_farming_knowledge`
- **Expected Outcome**: Inspects minimum temperatures across the 7-day forecast. Identifies freeze dates, recommends row covers or overhead sprinklers before dawn, and cites `frost_and_heat_protection.md`.

### Query 4: Sowing Timing & Soil Temperature
> *"What are the critical soil temperature and moisture thresholds before I sow my corn seeds?"*
- **Tools Triggered**: `search_farming_knowledge`, `get_weather_forecast`
- **Expected Outcome**: Cites minimum 10–12°C sustained soil temperature, warns against imbibitional chilling from cold rains within 48 hours of sowing, and cites `crop_calendar_and_sowing.md`.

### Query 5: Fungal Disease Outbreak Risk
> *"With recent high humidity and morning fog, what is the risk of late blight or fungal leaf spot on my potatoes and tomatoes?"*
- **Tools Triggered**: `get_weather_forecast`, `disease_risk_estimator`, `search_farming_knowledge`
- **Expected Outcome**: Computes pathogen risk index based on hours of relative humidity >85% and leaf wetness. Provides preventive cultural and bio-fungicide advice, citing `pest_and_fungal_disease_guide.md`.

### Query 6: Fertilizer & Topdressing Window
> *"I need to apply urea topdressing to my wheat field. Does the upcoming weather forecast support application?"*
- **Tools Triggered**: `get_weather_forecast`, `search_farming_knowledge`
- **Expected Outcome**: Recommends applying before light to moderate showers (5–10 mm) to incorporate nitrogen into root zones, while warning against applying before heavy downpours (>25 mm) to avoid nitrate runoff, citing `fertilizer_and_nutrient_timing.md`.

### Query 7: Heatwave Stress Mitigation
> *"A heatwave is forecasted with temperatures exceeding 36°C. How can I protect flowering vegetables from blossom drop?"*
- **Tools Triggered**: `get_weather_alerts`, `get_weather_forecast`, `search_farming_knowledge`
- **Expected Outcome**: Recommends deep morning pre-irrigation to maintain canopy transpirational cooling, shade netting, and avoiding midday soil disturbance, citing `frost_and_heat_protection.md`.

### Query 8: Location Override Query
> *"I also manage a satellite field in Fresno, California. Check the weather conditions and irrigation needs for corn in sandy soil there."*
- **Tools Triggered**: `geocode_location`, `get_weather_forecast`, `irrigation_advisor`
- **Expected Outcome**: Geocodes Fresno, pulls live local forecast, calculates sandy soil water holding capacity (recommending frequent, smaller pulses to prevent percolation loss).

### Query 9: Farm Profile Dynamic Update
> *"We just expanded our farm: update my profile with 25 hectares, Clay soil, and add Potato to our crops."*
- **Tools Triggered**: `update_farm_profile`, `get_farm_profile`
- **Expected Outcome**: Modifies SQLite farm profile record and confirms updated acreage and soil characteristics in conversational response.

### Query 10: Soil Compaction & Field Trafficability
> *"We received 30 mm of heavy rain yesterday. Can I drive my tractor into the clay field to cultivate weeds today?"*
- **Tools Triggered**: `get_weather_forecast`, `search_farming_knowledge`
- **Expected Outcome**: Strongly warns against heavy machinery on saturated clay soil to prevent destructive compaction, plow pan formation, and root zone asphyxiation.
