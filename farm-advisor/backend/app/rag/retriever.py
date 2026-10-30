import logging
from typing import List, Dict, Any, Optional
from app.config import settings
from app.rag.vectorstore import get_vectorstore

logger = logging.getLogger("farm_advisor.rag.retriever")

def retrieve_farming_knowledge(
    query: str,
    crop: Optional[str] = None,
    top_k: int = 4
) -> List[Dict[str, Any]]:
    """Retrieve top knowledge base chunks for an agronomic query with optional reranking."""
    vectorstore = get_vectorstore()
    
    # Optional metadata filtering
    filter_dict = None
    if crop:
        # Check if crop keyword matches metadata
        filter_dict = None  # Chroma semantic similarity handles crop names effectively in query
        
    try:
        search_query = f"{query} {crop}" if crop else query
        docs_with_scores = vectorstore.similarity_search_with_relevance_scores(
            search_query,
            k=max(top_k, 6) if settings.USE_RERANKER else top_k
        )
    except Exception as e:
        logger.warning("Similarity search with scores failed, falling back to basic similarity: %s", e)
        docs = vectorstore.similarity_search(search_query, k=top_k)
        docs_with_scores = [(d, 0.8) for d in docs]

    results = []
    for doc, score in docs_with_scores:
        results.append({
            "source": doc.metadata.get("source", "farming_kb"),
            "title": doc.metadata.get("title", "Agricultural Best Practices"),
            "category": doc.metadata.get("category", "Agronomy"),
            "crop": doc.metadata.get("crop", "General"),
            "content": doc.page_content,
            "score": round(float(score), 3) if score is not None else 0.8
        })

    # Optional NVIDIA Reranker
    if settings.USE_RERANKER and settings.NVIDIA_API_KEY and not settings.NVIDIA_API_KEY.startswith("nvapi-your-key"):
        try:
            from langchain_nvidia_ai_endpoints import NVIDIARerank
            from langchain_core.documents import Document
            
            logger.info("Applying NVIDIARerank model: %s", settings.NVIDIA_RERANK_MODEL)
            reranker = NVIDIARerank(
                model=settings.NVIDIA_RERANK_MODEL,
                api_key=settings.NVIDIA_API_KEY,
                base_url=settings.NVIDIA_BASE_URL,
                top_n=top_k
            )
            raw_docs = [
                Document(page_content=r["content"], metadata={"source": r["source"], "title": r["title"]})
                for r in results
            ]
            reranked = reranker.compress_documents(documents=raw_docs, query=query)
            
            reranked_results = []
            for r_doc in reranked:
                reranked_results.append({
                    "source": r_doc.metadata.get("source", "farming_kb"),
                    "title": r_doc.metadata.get("title", ""),
                    "category": r_doc.metadata.get("category", ""),
                    "crop": r_doc.metadata.get("crop", ""),
                    "content": r_doc.page_content,
                    "score": getattr(r_doc, "relevance_score", 0.9)
                })
            return reranked_results[:top_k]
        except Exception as e:
            logger.warning("NVIDIARerank execution failed, continuing with similarity results: %s", e)

    return results[:top_k]
