import logging
from typing import Dict, Any
from langchain_core.tools import tool
from app.rag.retriever import retrieve_farming_knowledge

logger = logging.getLogger("farm_advisor.tools.rag")

@tool
def search_farming_knowledge(query: str, crop: str = "") -> Dict[str, Any]:
    """Search the agronomic and extension farming knowledge base for guidance on crops, irrigation thresholds, disease symptoms, pest controls, or sowing requirements.
    
    Args:
        query: Specific agronomy question or concept (e.g., 'soil temperature for tomato sowing', 'late blight signs and fungicide spray timing').
        crop: Optional crop to prioritize (e.g. 'Tomato', 'Corn', 'Wheat', 'Potato').
    """
    try:
        results = retrieve_farming_knowledge(query=query, crop=crop, top_k=3)
        if not results:
            return {
                "status": "not_found",
                "message": "No relevant farming knowledge base documents matched the query.",
                "snippets": []
            }
            
        formatted_snippets = []
        sources = []
        for r in results:
            source_tag = r["source"]
            if source_tag not in sources:
                sources.append(source_tag)
            formatted_snippets.append({
                "source": source_tag,
                "title": r["title"],
                "text": r["content"]
            })
            
        return {
            "status": "success",
            "sources": sources,
            "count": len(formatted_snippets),
            "snippets": formatted_snippets
        }
    except Exception as e:
        logger.error("Knowledge base search failed: %s", e)
        return {
            "status": "error",
            "message": f"Could not perform knowledge search: {str(e)}"
        }
