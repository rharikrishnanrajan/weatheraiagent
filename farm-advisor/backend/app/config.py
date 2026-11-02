# ==============================================================================
# AgriPulse: Application Configuration Settings
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Reads environment variables from the `backend/.env` file.
# 2. Automatically resolves file paths (database, ChromaDB vectors, knowledge base docs).
# 3. Ensures target data directories exist on disk before starting up.
# 4. Uses Pydantic BaseSettings to validate configuration types and defaults.
# ==============================================================================

import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base backend directory: farm-advisor/backend
# Resolving .parent.parent from app/config.py points directly to farm-advisor/backend
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and backend/.env file.
    Default values are provided for easy local development.
    """
    # --------------------------------------------------------------------------
    # NVIDIA AI Endpoints (NIM) Configuration
    # --------------------------------------------------------------------------
    # API key obtained from build.nvidia.com
    NVIDIA_API_KEY: str = ""
    
    # Primary Chat LLM model used for agronomic reasoning and tool calling
    NVIDIA_CHAT_MODEL: str = "meta/llama-3.3-70b-instruct"
    
    # Embedding model used to convert text into numeric vectors for RAG search
    NVIDIA_EMBED_MODEL: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"
    
    # Base URL for NVIDIA AI Foundation Endpoints
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    
    # --------------------------------------------------------------------------
    # Optional Neural Reranking Configuration
    # --------------------------------------------------------------------------
    # When enabled, re-scores retrieved RAG documents for maximum relevance
    USE_RERANKER: bool = False
    NVIDIA_RERANK_MODEL: str = "nvidia/llama-3.2-nv-rerankqa-1b-v2"
    
    # --------------------------------------------------------------------------
    # Database and Vector Storage Paths
    # --------------------------------------------------------------------------
    # SQLite file storing farmer profile, message threads, and conversation history
    SQLITE_DB_PATH: str = str((BASE_DIR / "data" / "farm_advisor.db").resolve())
    
    # Directory storing Chroma vector embeddings for agricultural manuals
    CHROMA_DB_DIR: str = str((BASE_DIR / "data" / "chroma_db").resolve())
    
    # Directory containing markdown files for agricultural knowledge (RAG documents)
    KNOWLEDGE_BASE_DIR: str = str((BASE_DIR / "data" / "knowledge_base").resolve())
    
    # --------------------------------------------------------------------------
    # Web Server Network Settings
    # --------------------------------------------------------------------------
    HOST: str = "0.0.0.0"       # Listen on all local network interfaces
    PORT: int = 8000            # Port number for FastAPI
    DEBUG: bool = True          # Enable auto-reload and verbose debug logging in development

    # Pydantic configuration: link to backend/.env
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"          # Ignore extra environment variables not listed above
    )

    @field_validator("SQLITE_DB_PATH", "CHROMA_DB_DIR", "KNOWLEDGE_BASE_DIR", mode="after")
    @classmethod
    def resolve_relative_paths(cls, v: str) -> str:
        """
        Validator: converts any relative file paths into absolute paths anchored
        at BASE_DIR, preventing "File Not Found" errors when running from different folders.
        """
        p = Path(v)
        if not p.is_absolute():
            return str((BASE_DIR / p).resolve())
        return str(p.resolve())

# Instantiate the global settings object used across the backend
settings = Settings()

# Ensure required storage directories exist on disk
os.makedirs(os.path.dirname(settings.SQLITE_DB_PATH), exist_ok=True)
os.makedirs(settings.CHROMA_DB_DIR, exist_ok=True)
os.makedirs(settings.KNOWLEDGE_BASE_DIR, exist_ok=True)
