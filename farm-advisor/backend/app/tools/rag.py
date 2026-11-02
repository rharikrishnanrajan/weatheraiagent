# ==============================================================================
# AgriPulse: RAG Knowledge Search Tool
# ==============================================================================
# WHAT THIS FILE DOES:
# Provides the `search_farming_knowledge` agent tool, which lets the AI look up
# agronomic guidance from the local Chroma vector database.
#
# BEGINNER TIP: "RAG" stands for Retrieval-Augmented Generation.
# Instead of the AI just relying on what it learned during training, this tool
# lets it search a curated library of farming guides (PDFs, Markdown files) that
# YOU have uploaded. This makes the answers more accurate and locally relevant.
#
# How it works:
# 1. The user asks a question like "when should I apply urea on wheat?"
# 2. This tool converts the question into a vector (a list of numbers) using embeddings.
# 3. It searches the ChromaDB vector store for the most similar document chunks.
# 4. The most relevant text passages are returned for the AI to cite in its answer.
# ==============================================================================

import logging
from typing import Dict, Any
from langchain_core.tools import tool

# Retriever function defined in app/rag/retriever.py
from app.rag.retriever import retrieve_farming_knowledge

logger = logging.getLogger("farm_advisor.tools.rag")


# ==============================================================================
# AGENT TOOL: search_farming_knowledge
# ==============================================================================
@tool
def search_farming_knowledge(query: str, crop: str = "") -> Dict[str, Any]:
    """Search the agronomic and extension farming knowledge base for guidance on crops,
    irrigation thresholds, disease symptoms, pest controls, or sowing requirements.

    Args:
        query: Specific agronomy question or concept
               (e.g., 'soil temperature for tomato sowing',
                      'late blight signs and fungicide spray timing').
        crop: Optional crop name to prioritize in results
              (e.g. 'Tomato', 'Corn', 'Wheat', 'Potato').
    """
    try:
        # Run semantic similarity search in ChromaDB – returns top matching text chunks
        results = retrieve_farming_knowledge(query=query, crop=crop, top_k=3)

        if not results:
            # No relevant documents found for this query
            return {
                "status": "not_found",
                "message": "No relevant farming knowledge base documents matched the query.",
                "snippets": []
            }

        # Build clean snippet list and collect unique source file names for citations
        formatted_snippets = []
        sources = []
        for r in results:
            source_tag = r["source"]  # e.g. "irrigation_management_guide.md"
            if source_tag not in sources:
                sources.append(source_tag)  # Only add unique sources
            formatted_snippets.append({
                "source": source_tag,
                "title": r["title"],    # Human-readable title of the guide
                "text": r["content"]    # The actual relevant passage text
            })

        return {
            "status": "success",
            "sources": sources,             # List of source files cited
            "count": len(formatted_snippets),
            "snippets": formatted_snippets  # Retrieved text passages with metadata
        }

    except Exception as e:
        logger.error("Knowledge base search failed: %s", e)
        return {
            "status": "error",
            "message": f"Could not perform knowledge search: {str(e)}"
        }
