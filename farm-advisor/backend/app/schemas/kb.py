from pydantic import BaseModel, Field
from typing import List, Optional

class KnowledgeDoc(BaseModel):
    id: str
    filename: str
    title: str
    category: str
    crops: List[str]
    chunk_count: int
    created_at: str

class SearchQuery(BaseModel):
    query: str
    crop: Optional[str] = None
    top_k: int = 4

class SearchResult(BaseModel):
    document_id: str
    source: str
    crop: Optional[str]
    content: str
    score: Optional[float] = None

class IngestResponse(BaseModel):
    status: str
    documents_processed: int
    chunks_created: int
    collection_name: str
    details: Optional[str] = None
