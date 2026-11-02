# ==============================================================================
# AgriPulse: FastAPI Backend Server Entry Point
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Creates and configures the FastAPI web application instance.
# 2. Sets up application startup and shutdown lifecycle tasks (database setup & AI health checks).
# 3. Enables Cross-Origin Resource Sharing (CORS) so our React frontend can communicate with it.
# 4. Provides global exception handlers to gracefully catch API quota limits and errors.
# 5. Registers all API route endpoints (/api/chat, /api/weather, /api/profile, etc.).
# ==============================================================================

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import global settings (reads backend/.env file)
from app.config import settings

# Database initializers and AI model validators
from app.db.session import init_db
from app.agent.llm import validate_nvidia_config

# Import individual endpoint routers
from app.api.chat import router as chat_router
from app.api.profile import router as profile_router
from app.api.threads import router as threads_router
from app.api.weather import router as weather_router
from app.api.kb import router as kb_router

# ------------------------------------------------------------------------------
# STEP 1: CONFIGURE LOGGING
# ------------------------------------------------------------------------------
# Structured logging outputs timestamps, severity levels, and module names to terminal
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("farm_advisor.main")


# ------------------------------------------------------------------------------
# STEP 2: APPLICATION LIFESPAN (Startup & Shutdown)
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages background tasks before the app starts accepting traffic and after it stops.
    - On Startup: Automatically creates SQLite tables and verifies NVIDIA API keys.
    - On Shutdown: Cleans up any resources or logs termination.
    """
    logger.info("Initializing AgriPulse Farm Advisory Backend...")
    
    # 1. Initialize SQLite database tables (farm_profile, chat_threads, chat_messages)
    init_db()
    
    # 2. Test NVIDIA Model and tool-calling compatibility
    validation = validate_nvidia_config()
    logger.info("NVIDIA Model Validation Status: %s - %s", validation["status"], validation["message"])
    if validation["status"] == "warning":
        logger.warning("Agent operating in heuristic fallback mode. Set NVIDIA_API_KEY for neural LLaMA 3.3 NIM inference.")
    
    # Hand control over to FastAPI server
    yield
    
    # Code below runs when server is stopped (e.g. CTRL+C)
    logger.info("Shutting down AgriPulse Farm Advisory Backend.")


# ------------------------------------------------------------------------------
# STEP 3: INSTANTIATE FASTAPI APP
# ------------------------------------------------------------------------------
app = FastAPI(
    title="AgriPulse - Weather-Based Farming Advisory AI",
    description="Agentic Agronomy AI pairing live Open-Meteo weather with agricultural RAG and NVIDIA NIM reasoning.",
    version="1.0.0",
    lifespan=lifespan
)


# ------------------------------------------------------------------------------
# STEP 4: CORS (Cross-Origin Resource Sharing) MIDDLEWARE
# ------------------------------------------------------------------------------
# Allows our frontend (typically running on http://localhost:5173) to send requests
# to this backend (running on http://localhost:8000) without browser security blocks.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Allow all origins in local development
    allow_credentials=True,     # Allow cookies and authentication headers
    allow_methods=["*"],        # Allow GET, POST, PUT, DELETE, OPTIONS, etc.
    allow_headers=["*"],        # Allow all client request headers
)


# ------------------------------------------------------------------------------
# STEP 5: GLOBAL EXCEPTION HANDLER
# ------------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches uncaught exceptions across any endpoint and translates them into clean,
    user-friendly JSON error messages instead of crashing the server.
    """
    err_str = str(exc)
    err_lower = err_str.lower()
    
    # Handle rate limiting (HTTP 429) from NVIDIA AI endpoints
    if "429" in err_lower or "too many requests" in err_lower or "rate limit" in err_lower:
        logger.error("NVIDIA NIM Rate Limit Exceeded (429): %s", exc)
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate Limit Exceeded",
                "message": "NVIDIA AI Endpoints rate limit reached. Please wait a few moments before retrying.",
                "details": err_str
            }
        )
    # Handle invalid or missing API credentials (HTTP 401)
    elif "401" in err_lower or "unauthorized" in err_lower or "invalid api key" in err_lower:
        logger.error("NVIDIA NIM Authentication Failure (401): %s", exc)
        return JSONResponse(
            status_code=401,
            content={
                "error": "Authentication Failed",
                "message": "Invalid or missing NVIDIA_API_KEY. Please verify backend/.env settings.",
                "details": err_str
            }
        )
    # Handle upstream AI service downtime (HTTP 502/503)
    elif "503" in err_lower or "502" in err_lower or "service unavailable" in err_lower:
        logger.error("NVIDIA NIM Service Unavailable: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service Temporarily Unavailable",
                "message": "The upstream AI endpoint is temporarily unreachable. Please retry shortly.",
                "details": err_str
            }
        )

    # General unhandled server error (HTTP 500)
    logger.error("Unhandled Exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your farming request.",
            "details": err_str
        }
    )


# ------------------------------------------------------------------------------
# STEP 6: MOUNT API ROUTERS
# ------------------------------------------------------------------------------
# Group endpoints under the /api prefix
app.include_router(chat_router, prefix="/api")        # /api/chat - AI conversations & SSE streaming
app.include_router(profile_router, prefix="/api")     # /api/profile - Farmer profile & soil parameters
app.include_router(threads_router, prefix="/api")     # /api/threads - Chat history & session management
app.include_router(weather_router, prefix="/api")     # /api/weather - Live forecasts & agricultural alerts
app.include_router(kb_router, prefix="/api")          # /api/kb - Knowledge base document indexing & search


# ------------------------------------------------------------------------------
# STEP 7: HEALTH CHECK ENDPOINT
# ------------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    """
    GET /api/health
    Provides an operational pulse check for monitoring systems, reporting
    database connectivity and current NVIDIA AI model status.
    """
    nvidia_status = validate_nvidia_config()
    return {
        "status": "healthy",
        "service": "AgriPulse Farm Advisory Backend",
        "version": "1.0.0",
        "nvidia_config": nvidia_status,
        "database": {
            "sqlite_path": settings.SQLITE_DB_PATH,
            "chroma_dir": settings.CHROMA_DB_DIR
        }
    }


# ------------------------------------------------------------------------------
# STEP 8: DIRECT EXECUTION ENTRY POINT
# ------------------------------------------------------------------------------
# Allows running the backend directly via: python app/main.py
if __name__ == "__main__":
    import uvicorn
    # Start ASGI web server using configured host and port
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
