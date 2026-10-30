import logging
import hashlib
import numpy as np
from typing import List
from langchain_core.embeddings import Embeddings
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_chroma import Chroma
from app.config import settings

logger = logging.getLogger("farm_advisor.rag.vectorstore")

COLLECTION_NAME = "farming_knowledge"

class DeterministicFallbackEmbeddings(Embeddings):
    """Deterministic fallback embeddings when NVIDIA API key is not yet configured.
    Generates a consistent 1024-dimensional normalized vector for test and offline usage.
    """
    def __init__(self, dimension: int = 1024):
        self.dimension = dimension

    def _embed_text(self, text: str) -> List[float]:
        # Generate pseudorandom vector seeded by MD5 hash of text
        md5_int = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        rng = np.random.default_rng(md5_int % (2**32))
        vec = rng.standard_normal(self.dimension)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_text(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_text(text)

def get_embeddings_model() -> Embeddings:
    """Return NVIDIAEmbeddings if configured, else fallback embedder."""
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

def get_vectorstore() -> Chroma:
    """Return persistent Chroma vectorstore instance."""
    embeddings = get_embeddings_model()
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_DB_DIR
    )
