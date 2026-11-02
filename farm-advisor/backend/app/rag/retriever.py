# ==============================================================================
# AgriPulse: RAG Retriever – Semantic Knowledge Base Search
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Takes a natural-language question and searches the ChromaDB vector store
#    for the most semantically similar document chunks.
# 2. Optionally uses the NVIDIA Reranker model to re-rank results for precision.
# 3. Returns formatted text passages with source file names for citations.
#
# BEGINNER TIP: "Retrieval" is the "R" in RAG (Retrieval-Augmented Generation).
# This module acts like a smart search engine over your farming guides.
# Unlike a keyword search, it understands meaning – so a query like
# "when should I water potatoes?" will match a passage that says
# "potato crop water requirement peaks at tuber initiation" even though
# the words don't exactly match.
# ==============================================================================

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
    """
    Performs semantic similarity search over the ChromaDB vector store and returns
    the top-k most relevant document chunks for the given agricultural query.

    Workflow:
    1. Connect to ChromaDB vector store (already loaded with embedded chunks).
    2. Run similarity_search_with_relevance_scores() to get documents + scores.
    3. Optionally re-rank via NVIDIA Reranker for higher precision.
    4. Return formatted results with source file, title, and text content.

    Args:
        query: The agronomy question or topic (e.g. 'late blight treatment options').
        crop: Optional crop name to append to the query for better targeting
              (e.g. 'Tomato' → searches "late blight treatment options Tomato").
        top_k: Maximum number of results to return (default: 4).

    Returns:
        List[dict]: Each entry has keys: source, title, category, crop, content, score.
    """
    vectorstore = get_vectorstore()

    # Append crop name to the search query for better semantic targeting
    search_query = f"{query} {crop}" if crop else query

    try:
        # similarity_search_with_relevance_scores returns (Document, float) tuples
        # - If USE_RERANKER is True: fetch more than top_k initially so the reranker
        #   has a bigger pool to choose from (k candidates = 6+)
        # - Otherwise: just fetch exactly top_k
        docs_with_scores = vectorstore.similarity_search_with_relevance_scores(
            search_query,
            k=max(top_k, 6) if settings.USE_RERANKER else top_k
        )
    except Exception as e:
        # Fallback: some Chroma versions don't support the scores variant
        logger.warning("Similarity search with scores failed, falling back to basic similarity: %s", e)
        docs = vectorstore.similarity_search(search_query, k=top_k)
        docs_with_scores = [(d, 0.8) for d in docs]  # Assign default score 0.8

    # Convert (Document, score) tuples into clean dictionaries
    results = []
    for doc, score in docs_with_scores:
        results.append({
            "source": doc.metadata.get("source", "farming_kb"),      # Source filename
            "title": doc.metadata.get("title", "Agricultural Best Practices"),
            "category": doc.metadata.get("category", "Agronomy"),
            "crop": doc.metadata.get("crop", "General"),
            "content": doc.page_content,                              # The retrieved text passage
            "score": round(float(score), 3) if score is not None else 0.8  # Relevance score 0–1
        })

    # ------------------------------------------------------------------
    # OPTIONAL: NVIDIA RERANKER (cross-encoder re-scoring for precision)
    # ------------------------------------------------------------------
    # If enabled in .env (USE_RERANKER=true), the reranker re-scores each
    # retrieved document specifically against the original query using a
    # cross-encoder model (much slower but more precise than bi-encoder similarity).
    # ------------------------------------------------------------------
    if settings.USE_RERANKER and settings.NVIDIA_API_KEY and not settings.NVIDIA_API_KEY.startswith("nvapi-your-key"):
        try:
            from langchain_nvidia_ai_endpoints import NVIDIARerank
            from langchain_core.documents import Document

            logger.info("Applying NVIDIARerank model: %s", settings.NVIDIA_RERANK_MODEL)
            reranker = NVIDIARerank(
                model=settings.NVIDIA_RERANK_MODEL,
                api_key=settings.NVIDIA_API_KEY,
                base_url=settings.NVIDIA_BASE_URL,
                top_n=top_k   # Return only the top N after reranking
            )

            # Convert our result dicts back into LangChain Document objects for the reranker
            raw_docs = [
                Document(
                    page_content=r["content"],
                    metadata={"source": r["source"], "title": r["title"]}
                )
                for r in results
            ]

            # compress_documents returns the top_n most relevant documents
            reranked = reranker.compress_documents(documents=raw_docs, query=query)

            # Re-format reranked results back into our standard dictionary shape
            reranked_results = []
            for r_doc in reranked:
                reranked_results.append({
                    "source": r_doc.metadata.get("source", "farming_kb"),
                    "title": r_doc.metadata.get("title", ""),
                    "category": r_doc.metadata.get("category", ""),
                    "crop": r_doc.metadata.get("crop", ""),
                    "content": r_doc.page_content,
                    "score": getattr(r_doc, "relevance_score", 0.9)   # Reranker score
                })
            return reranked_results[:top_k]

        except Exception as e:
            # If reranking fails for any reason, gracefully fall through to standard results
            logger.warning("NVIDIARerank execution failed, continuing with similarity results: %s", e)

    # Return top_k results from the original similarity search (or after failed rerank)
    return results[:top_k]
