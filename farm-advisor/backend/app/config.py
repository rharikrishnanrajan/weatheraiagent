import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base backend directory: farm-advisor/backend
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # NVIDIA AI Endpoints
    NVIDIA_API_KEY: str = ""
    NVIDIA_CHAT_MODEL: str = "meta/llama-3.3-70b-instruct"
    NVIDIA_EMBED_MODEL: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    
    # Reranking configuration
    USE_RERANKER: bool = False
    NVIDIA_RERANK_MODEL: str = "nvidia/llama-3.2-nv-rerankqa-1b-v2"
    
    # Storage & DB
    SQLITE_DB_PATH: str = str((BASE_DIR / "data" / "farm_advisor.db").resolve())
    CHROMA_DB_DIR: str = str((BASE_DIR / "data" / "chroma_db").resolve())
    KNOWLEDGE_BASE_DIR: str = str((BASE_DIR / "data" / "knowledge_base").resolve())
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("SQLITE_DB_PATH", "CHROMA_DB_DIR", "KNOWLEDGE_BASE_DIR", mode="after")
    @classmethod
    def resolve_relative_paths(cls, v: str) -> str:
        p = Path(v)
        if not p.is_absolute():
            return str((BASE_DIR / p).resolve())
        return str(p.resolve())

settings = Settings()

# Ensure directories exist
os.makedirs(os.path.dirname(settings.SQLITE_DB_PATH), exist_ok=True)
os.makedirs(settings.CHROMA_DB_DIR, exist_ok=True)
os.makedirs(settings.KNOWLEDGE_BASE_DIR, exist_ok=True)
