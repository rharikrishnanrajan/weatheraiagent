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
router = APIRouter(prefix="/kb", tags=["Knowledge Base"])

@router.get("/documents", response_model=List[Dict[str, Any]])
def get_documents():
    """List all knowledge base documents with metadata, crops, and chunk estimates."""
    try:
        return list_kb_documents()
    except Exception as e:
        logger.error("Error listing KB docs: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a new agricultural document (.md, .txt, .pdf) to the knowledge base and re-index."""
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

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Re-index documents
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
    """Trigger manual vector ingestion of all documents into Chroma."""
    try:
        res = ingest_documents()
        return res
    except Exception as e:
        logger.error("Ingestion failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.post("/search", response_model=List[Dict[str, Any]])
def search_knowledge(payload: SearchQuery):
    """Semantic search against the agricultural knowledge base with optional crop filter."""
    try:
        results = retrieve_farming_knowledge(
            query=payload.query,
            crop=payload.crop,
            top_k=payload.top_k
        )
        return results
    except Exception as e:
        logger.error("Knowledge base search failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
