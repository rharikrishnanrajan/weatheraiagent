# ==============================================================================
# AgriPulse: RAG Document Ingestion Pipeline
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Reads agricultural guide files (.md, .txt, .pdf) from the knowledge_base directory.
# 2. Splits each document into small text chunks (~700 characters) for vector embedding.
# 3. Tags each chunk with metadata (source file, category, relevant crops).
# 4. Stores all chunks in the local ChromaDB vector store for semantic search.
# 5. Lists indexed documents for the /api/kb/documents endpoint.
#
# BEGINNER TIP: "Ingestion" is the process of loading documents into the AI's
# searchable memory. Think of it like adding books to a library catalog.
# Once ingested, the AI can find relevant passages using semantic search.
#
# WORKFLOW:
#   raw .md/.pdf files  →  extract text  →  split into chunks
#   →  tag with metadata  →  embed into vectors  →  store in ChromaDB
# ==============================================================================

import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from app.config import settings
from app.rag.vectorstore import get_vectorstore, COLLECTION_NAME

logger = logging.getLogger("farm_advisor.rag.ingest")


def extract_text_from_file(file_path: Path) -> str:
    """
    Reads a file and returns its full plain text content.
    Supports Markdown (.md), plain text (.txt), and PDF (.pdf).

    Args:
        file_path: Path object pointing to the file.

    Returns:
        str: The full text content of the file.
    """
    suffix = file_path.suffix.lower()

    if suffix in [".md", ".txt"]:
        # Read Markdown or plain text files directly as UTF-8 text
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif suffix == ".pdf":
        # PDFs require a special reader to extract text from each page
        reader = PdfReader(str(file_path))
        text_parts = []
        for i, page in enumerate(reader.pages):
            p_text = page.extract_text()
            if p_text:
                text_parts.append(p_text)
        # Join all page text with double newlines to preserve structure
        return "\n\n".join(text_parts)

    else:
        logger.warning("Unsupported file type: %s", suffix)
        return ""  # Return empty string for unsupported formats


def infer_crops_and_category(filename: str, content: str) -> tuple[str, str]:
    """
    Automatically determines which crops and knowledge category a document covers
    by scanning the filename and the first 1000 characters of the document.

    Args:
        filename: The file name (e.g. 'irrigation_management_guide.md').
        content: The full text of the document.

    Returns:
        tuple: (crop_string, category_string)
               e.g. ("Tomato, Wheat", "Irrigation & Water")
    """
    crops = []
    # Known crops to scan for in the document text
    known_crops = ["tomato", "corn", "maize", "wheat", "rice", "potato", "soybean", "cotton", "onion"]
    # Search in both filename and beginning of content for crop mentions
    lower_content = (filename + " " + content[:1000]).lower()
    for c in known_crops:
        if c in lower_content:
            crops.append(c.capitalize())

    # Join matched crops into a comma-separated string (or use generic label)
    crop_str = ", ".join(crops) if crops else "General Agriculture"

    # Determine the knowledge category by inspecting the filename keywords
    fname_lower = filename.lower()
    if "irrigation" in fname_lower or "water" in fname_lower:
        category = "Irrigation & Water"
    elif "pest" in fname_lower or "disease" in fname_lower or "fungal" in fname_lower:
        category = "Pest & Disease Control"
    elif "fertilizer" in fname_lower or "nutrient" in fname_lower:
        category = "Soil & Fertilizer"
    elif "frost" in fname_lower or "heat" in fname_lower or "weather" in fname_lower:
        category = "Weather Protection"
    elif "sowing" in fname_lower or "calendar" in fname_lower or "planting" in fname_lower:
        category = "Sowing & Planting"
    else:
        category = "Agronomic Advisory"   # Default catch-all category

    return crop_str, category


def ingest_documents(kb_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Main ingestion pipeline: scans the knowledge_base folder, parses all files,
    splits them into chunks, and batch-uploads to ChromaDB.

    Args:
        kb_dir: Optional override path to the knowledge base directory.
                Defaults to settings.KNOWLEDGE_BASE_DIR from .env.

    Returns:
        dict: Summary of the ingestion result with status, document count, chunk count.
    """
    target_dir = Path(kb_dir or settings.KNOWLEDGE_BASE_DIR)

    # Guard: make sure the directory exists before trying to read it
    if not target_dir.exists():
        logger.warning("Knowledge base directory does not exist: %s", target_dir)
        return {"status": "error", "message": f"Directory not found: {target_dir}"}

    # Collect all supported document files in the directory
    files = (
        list(target_dir.glob("*.md")) +   # Markdown files
        list(target_dir.glob("*.txt")) +  # Plain text files
        list(target_dir.glob("*.pdf"))    # PDF files
    )

    if not files:
        logger.info("No documents found to ingest in %s", target_dir)
        return {"status": "no_files", "documents_processed": 0, "chunks_created": 0}

    # ------------------------------------------------------------------
    # TEXT SPLITTER CONFIGURATION
    # Splits long documents into overlapping chunks for better retrieval.
    # - chunk_size: ~700 characters per chunk (fits within embedding context)
    # - chunk_overlap: 90 characters of overlap so context isn't lost at boundaries
    # - separators: try to split at section headers first, then paragraphs, then sentences
    # ------------------------------------------------------------------
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=90,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "]
    )

    docs_to_add: List[Document] = []   # All Document objects ready for ChromaDB
    processed_count = 0                # How many source files were processed

    for f in files:
        content = extract_text_from_file(f)
        if not content.strip():
            continue  # Skip empty or unreadable files

        # Infer metadata tags from the document
        crops, category = infer_crops_and_category(f.name, content)

        # Split the document into overlapping text chunks
        chunks = text_splitter.split_text(content)

        for idx, chunk in enumerate(chunks):
            # Wrap each chunk as a LangChain Document object with rich metadata
            doc = Document(
                page_content=chunk,
                metadata={
                    "source": f.name,                               # Original filename
                    "title": f.stem.replace("_", " ").title(),     # Human-readable title
                    "category": category,                           # Topical category
                    "crop": crops,                                  # Applicable crops
                    "chunk_id": f"{f.stem}_{idx}"                  # Unique ID per chunk
                }
            )
            docs_to_add.append(doc)

        processed_count += 1

    if not docs_to_add:
        return {"status": "success", "documents_processed": 0, "chunks_created": 0}

    # ------------------------------------------------------------------
    # BATCH UPLOAD TO CHROMADB
    # We upload in batches of 20 to avoid overwhelming the embedding API.
    # If we hit a rate limit (HTTP 429), we back off and retry.
    # ------------------------------------------------------------------
    vectorstore = get_vectorstore()
    batch_size = 20  # Number of chunks per API batch

    for i in range(0, len(docs_to_add), batch_size):
        batch = docs_to_add[i: i + batch_size]
        max_retries = 3

        for attempt in range(max_retries):
            try:
                vectorstore.add_documents(batch)
                break  # Success – move to next batch
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "rate limit" in err_str:
                    # NVIDIA API rate limit – wait longer on each subsequent retry
                    wait_time = 3.0 * (attempt + 1)
                    logger.warning("Rate limit hit during vectorstore ingestion, backing off for %.0f seconds...", wait_time)
                    time.sleep(wait_time)
                else:
                    if attempt == max_retries - 1:
                        # Final attempt failed – log and re-raise
                        logger.error("Failed adding batch to vectorstore: %s", e)
                        raise
                    time.sleep(1.0)  # Short pause before retrying non-rate-limit errors

    logger.info(
        "Ingestion completed: %d documents, %d chunks into collection %s",
        processed_count, len(docs_to_add), COLLECTION_NAME
    )

    return {
        "status": "success",
        "documents_processed": processed_count,
        "chunks_created": len(docs_to_add),
        "collection_name": COLLECTION_NAME
    }


def list_kb_documents(kb_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns a summary list of all documents in the knowledge base directory.
    Used by the /api/kb/documents endpoint to populate the frontend document table.

    Args:
        kb_dir: Optional override path to the knowledge base directory.

    Returns:
        List[dict]: Each item contains filename, title, category, crops, size, chunk_count.
    """
    target_dir = Path(kb_dir or settings.KNOWLEDGE_BASE_DIR)
    if not target_dir.exists():
        return []

    results = []
    files = (
        list(target_dir.glob("*.md")) +
        list(target_dir.glob("*.txt")) +
        list(target_dir.glob("*.pdf"))
    )

    for f in files:
        stat = f.stat()                        # Get file system metadata (size, timestamps)
        content = extract_text_from_file(f)
        crops, category = infer_crops_and_category(f.name, content)

        results.append({
            "id": f.name,
            "filename": f.name,
            "title": f.stem.replace("_", " ").title(),   # e.g. "Irrigation Management Guide"
            "category": category,
            "crops": [c.strip() for c in crops.split(",") if c.strip()],  # List form
            "size_bytes": stat.st_size,
            "chunk_count": max(1, len(content) // 600),  # Estimated number of chunks
            "created_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
        })

    # Sort alphabetically by filename for consistent display order
    return sorted(results, key=lambda x: x["filename"])
