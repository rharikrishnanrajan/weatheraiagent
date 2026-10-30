import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.session import init_db
from app.agent.llm import validate_nvidia_config
from app.api.chat import router as chat_router
from app.api.profile import router as profile_router
from app.api.threads import router as threads_router
from app.api.weather import router as weather_router
from app.api.kb import router as kb_router

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("farm_advisor.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info("Initializing AgriPulse Farm Advisory Backend...")
    # Initialize SQLite tables
    init_db()
    
    # Validate NVIDIA Model and Tool Binding
    validation = validate_nvidia_config()
    logger.info("NVIDIA Model Validation Status: %s - %s", validation["status"], validation["message"])
    if validation["status"] == "warning":
        logger.warning("Agent operating in heuristic fallback mode. Set NVIDIA_API_KEY for neural LLaMA 3.3 NIM inference.")
    
    yield
    logger.info("Shutting down AgriPulse Farm Advisory Backend.")

app = FastAPI(
    title="AgriPulse - Weather-Based Farming Advisory AI",
    description="Agentic Agronomy AI pairing live Open-Meteo weather with agricultural RAG and NVIDIA NIM reasoning.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware allowing frontend Vite dev server (and any origin in development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Error Handling for NVIDIA API Limits & Rate Exceeded
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    err_str = str(exc)
    err_lower = err_str.lower()
    
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

    logger.error("Unhandled Exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your farming request.",
            "details": err_str
        }
    )

# Include API Routers
app.include_router(chat_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(threads_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(kb_router, prefix="/api")

@app.get("/api/health")
def health_check():
    """System health check endpoint."""
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
