# ==============================================================================
# AgriPulse: Knowledge Base & Document Ingestion API (/api/kb)
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Lists all agricultural extension manuals currently loaded in the system.
# 2. Handles document uploading (.md, .txt, .pdf) from farmers or researchers.
# 3. Triggers vectorization and storage in the ChromaDB vector database.
# 4. Exposes an interactive semantic search endpoint for testing RAG retrieval.
# ==============================================================================

import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File

from app.config import settings
from app.schemas.kb import SearchQuery
from app.rag.ingest import list_kb_documents, ingest_documents
from app.rag.retriever import retrieve_farming_knowledge

logger = logging.getLogger("farm_advisor.api.kb")

# Router mounted at /api/kb
router = APIRouter(prefix="/kb", tags=["Knowledge Base"])


@router.get("/documents", response_model=List[Dict[str, Any]])
def get_documents():
    """
    GET /api/kb/documents
    Lists all agricultural documents in backend/data/knowledge_base with file size,
    crop tags, and chunk count estimates.
    """
    try:
        return list_kb_documents()
    except Exception as e:
        logger.error("Error listing KB docs: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    POST /api/kb/upload
    Uploads a new agronomy document (.md, .txt, .pdf) and immediately parses,
    chunks, and embeds it into ChromaDB for instant agent search.
    """
    try:
        filename = file.filename or "uploaded_doc.txt"
        suffix = Path(filename).suffix.lower()
        if suffix not in [".md", ".txt", ".pdf"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension '{suffix}'. Only .md, .txt, and .pdf are supported."
            )

        kb_dir = Path(settings.KNOWLEDGE_BASE_DIR)
        kb_dir.mkdir(parents=True, exist_ok=True)
        target_path = kb_dir / filename

        # Save uploaded file to disk
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Re-index all documents into ChromaDB
        ingest_res = ingest_documents()
        return {
            "status": "success",
            "filename": filename,
            "size_bytes": target_path.stat().st_size,
            "ingestion_result": ingest_res
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")


@router.post("/ingest")
def trigger_ingest():
    """
    POST /api/kb/ingest
    Manually triggers re-indexing of all documents in the knowledge base folder.
    """
    try:
        res = ingest_documents()
        return res
    except Exception as e:
        logger.error("Ingestion failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/search", response_model=List[Dict[str, Any]])
def search_knowledge(payload: SearchQuery):
    """
    POST /api/kb/search
    Performs semantic vector search across farming guides with optional crop filters.
    Returns matched paragraphs, relevance score, and source filename.
    """
    try:
        results = retrieve_farming_knowledge(
            query=payload.query,
            k=payload.k,
            crop_filter=payload.crop_filter
        )
        return results
    except Exception as e:
        logger.error("Knowledge search failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
