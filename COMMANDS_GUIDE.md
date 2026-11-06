# ==============================================================================
# AgriPulse Beginner's Command & Execution Guide
# ==============================================================================
# This guide contains all the terminal commands and explanations required to
# install, configure, build, run, and test AgriPulse on Windows, macOS, or Linux.
# ==============================================================================

## 📌 System Prerequisites
Ensure you have the following installed on your computer:
1. **Python 3.10+** (Verify via: `python --version`)
2. **Node.js 18+** & npm (Verify via: `node -v` and `npm -v`)
3. **Git** (Verify via: `git --version`)

---

## 🚀 1. Quick Start: Running the Project in 2 Steps

### Step 1: Start the Backend (Terminal 1)
```powershell
# Navigate to the backend folder
cd "d:\Weather AI Agent\farm-advisor\backend"

# (Optional) Activate your virtual environment if created
# Windows:
.\.venv\Scripts\Activate.ps1
# Mac/Linux:
# source .venv/bin/activate

# Start the FastAPI server with auto-reload
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
> **Backend URL:** http://localhost:8000  
> **Interactive API Docs (Swagger UI):** http://localhost:8000/docs  
> **Health Check:** http://localhost:8000/api/health  

---

### Step 2: Start the Frontend (Terminal 2)
```powershell
# Open a second terminal and navigate to the frontend folder
cd "d:\Weather AI Agent\farm-advisor\frontend"

# Install dependencies (only required on first setup)
npm install

# Start the Vite development server
npm run dev
```
> **Frontend App URL:** http://localhost:5173  

---

## 🛠️ 2. First-Time Installation & Environment Setup

### Setting up the Python Virtual Environment
```powershell
cd "d:\Weather AI Agent\farm-advisor\backend"

# Create a fresh Python virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows Command Prompt:
.\.venv\Scripts\activate.bat
# macOS / Linux:
source .venv/bin/activate

# Upgrade pip to latest version
python -m pip install --upgrade pip

# Install all backend dependencies
pip install -r requirements.txt
```

### Configuring Environment Variables (.env)
```powershell
cd "d:\Weather AI Agent\farm-advisor\backend"

# Copy the example environment file if .env does not exist
Copy-Item .env.example .env
```
Inside `farm-advisor/backend/.env`:
```env
# Optional: Get a free key from build.nvidia.com for LLaMA 3.3 70B
# If left empty, AgriPulse automatically runs in zero-dependency offline fallback mode!
NVIDIA_API_KEY=

# Server defaults
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

---

## 📚 3. Knowledge Base Ingestion (RAG ChromaDB)

AgriPulse includes curated agronomic guides for irrigation, sowing, pest management, and frost protection located in `backend/data/knowledge_base/`.

To re-index or embed all knowledge documents into the local Chroma vector database:
```powershell
cd "d:\Weather AI Agent\farm-advisor\backend"

# Run the standalone ingestion script
python scripts/ingest.py
```

---

## 🧪 4. Testing Commands

AgriPulse includes automated tests for meteorological tools, FAO-56 irrigation equations, and API integration:

```powershell
cd "d:\Weather AI Agent\farm-advisor\backend"

# Run all test suites
pytest

# Run tests with verbose output and print statements
pytest -v -s

# Run tool calculation tests only
pytest tests/test_tools.py

# Run API endpoint integration tests
pytest tests/test_api_integration.py
```

---

## 🏗️ 5. Frontend Production Build & Linting

```powershell
cd "d:\Weather AI Agent\farm-advisor\frontend"

# Build production bundle
npm run build

# Preview production build locally
npm run preview

# Run linter
npm run lint
```

---

## 🧭 6. Key Application Endpoints & Ports

| Component | URL | Purpose |
| :--- | :--- | :--- |
| **Web UI** | `http://localhost:5173` | Interactive farmer chat, live weather radar, and profile settings |
| **FastAPI Backend** | `http://localhost:8000` | Core agent engine and tool execution |
| **Swagger Docs** | `http://localhost:8000/docs` | Interactive API documentation to test endpoints directly |
| **Health Check** | `http://localhost:8000/api/health` | Diagnostic status of SQLite, ChromaDB, and NVIDIA NIM |
| **Live Weather API**| `http://localhost:8000/api/weather` | Open-Meteo forecasts and hazard alerts |
| **Chat API (SSE)** | `http://localhost:8000/api/chat` | Server-Sent Events streaming conversational agent |

