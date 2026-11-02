# ==============================================================================
# AgriPulse: RAG Vector Store & Embeddings Client
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Connects to ChromaDB for persistent vector storage on local disk.
# 2. Uses NVIDIA AI Endpoints (nvidia/llama-3.2-nv-embedqa-1b-v2) for neural embeddings.
# 3. Includes `DeterministicFallbackEmbeddings` so vector search never crashes even
#    if the developer hasn't configured an NVIDIA API key yet!
# ==============================================================================

import logging
import hashlib
import numpy as np
from typing import List
from langchain_core.embeddings import Embeddings
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_chroma import Chroma
from app.config import settings

logger = logging.getLogger("farm_advisor.rag.vectorstore")

# Name of the Chroma collection storing agronomic documents
COLLECTION_NAME = "farming_knowledge"


# ==============================================================================
# FALLBACK EMBEDDINGS CLASS (Zero API Key Requirement)
# ==============================================================================
class DeterministicFallbackEmbeddings(Embeddings):
    """
    Deterministic fallback embeddings used when NVIDIA_API_KEY is not configured.
    Converts any text into a reproducible 1024-dimensional normalized vector
    using an MD5 seed and standard Gaussian distribution.
    """
    def __init__(self, dimension: int = 1024):
        self.dimension = dimension

    def _embed_text(self, text: str) -> List[float]:
        # Generate pseudorandom vector seeded by MD5 hash of text
        md5_int = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        rng = np.random.default_rng(md5_int % (2**32))
        vec = rng.standard_normal(self.dimension)
        # Normalize vector to unit length
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_text(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_text(text)


# ==============================================================================
# EMBEDDINGS MODEL FACTORY
# ==============================================================================
def get_embeddings_model() -> Embeddings:
    """
    Factory function: Returns NVIDIAEmbeddings if an active API key is provided,
    otherwise returns DeterministicFallbackEmbeddings.
    """
    api_key = settings.NVIDIA_API_KEY
    if api_key and not api_key.startswith("nvapi-your-key"):
        try:
            logger.info("Initializing NVIDIAEmbeddings with model: %s", settings.NVIDIA_EMBED_MODEL)
            return NVIDIAEmbeddings(
                model=settings.NVIDIA_EMBED_MODEL,
                api_key=api_key,
                base_url=settings.NVIDIA_BASE_URL
            )
        except Exception as e:
            logger.warning("Failed to initialize NVIDIAEmbeddings, using fallback: %s", e)
            return DeterministicFallbackEmbeddings()
    else:
        logger.info("NVIDIA_API_KEY not set or is placeholder; using deterministic fallback embeddings.")
        return DeterministicFallbackEmbeddings()


# ==============================================================================
# CHROMA VECTOR STORE SINGLETON
# ==============================================================================
def get_vectorstore() -> Chroma:
    """
    Returns a persistent Chroma vector store instance stored on disk at backend/data/chroma_db.
    """
    embeddings = get_embeddings_model()
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_DB_DIR
    )
