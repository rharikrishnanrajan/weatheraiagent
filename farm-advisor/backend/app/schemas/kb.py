# ==============================================================================
# AgriPulse: Knowledge Base Schemas (Pydantic Models)
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Models agricultural document metadata (filename, crops covered, chunk count).
# 2. Defines search request payload for semantic similarity queries against ChromaDB.
# 3. Models search results with relevance scores and document excerpts.
# 4. Reports document ingestion status and vector counts.
# ==============================================================================

from pydantic import BaseModel, Field
from typing import List, Optional


class KnowledgeDoc(BaseModel):
    """Metadata representing an indexed agricultural reference guide."""
    id: str = Field(description="Unique document ID (usually derived from filename)")
    filename: str = Field(description="Original filename on disk (e.g. 'irrigation_management_guide.md')")
    title: str = Field(description="Extracted or human-friendly document title")
    category: str = Field(description="Subject category (e.g. 'Irrigation', 'Pest Control', 'Fertilizer')")
    crops: List[str] = Field(description="List of crops explicitly referenced in this guide")
    chunk_count: int = Field(description="Number of text chunks embedded into ChromaDB")
    created_at: str = Field(description="File modification timestamp")


class SearchQuery(BaseModel):
    """Request payload for semantic vector search in the knowledge base."""
    query: str = Field(description="Agronomic question or topic to search (e.g. 'when to water corn')")
    crop: Optional[str] = Field(default=None, description="Optional crop filter to narrow down results")
    top_k: int = Field(default=4, ge=1, le=20, description="Maximum number of relevant chunks to retrieve")


class SearchResult(BaseModel):
    """A single matched passage returned from vector search."""
    document_id: str = Field(description="Identifier of parent document")
    source: str = Field(description="Original source file name for citation")
    crop: Optional[str] = Field(default=None, description="Relevant crop tag")
    content: str = Field(description="The matching text passage")
    score: Optional[float] = Field(default=None, description="Similarity or relevance score (higher = closer match)")


class IngestResponse(BaseModel):
    """Summary report returned after running vector store ingestion."""
    status: str = Field(description="Overall status: 'success' or 'error'")
    documents_processed: int = Field(description="Count of files parsed from knowledge_base directory")
    chunks_created: int = Field(description="Total vector embeddings generated and saved to ChromaDB")
    collection_name: str = Field(description="ChromaDB collection identifier")
    details: Optional[str] = Field(default=None, description="Optional descriptive status or error details")
