"""Pydantic models for KB operations."""
from pydantic import BaseModel, Field
from datetime import datetime


class KBUploadRequest(BaseModel):
    """Request model for KB document upload."""
    workspace_id: str
    title: str | None = None
    url: str | None = None
    tags: list[str] = Field(default_factory=list)


class KBChunk(BaseModel):
    """Metadata for a KB chunk stored in Qdrant."""
    chunk_id: str
    workspace_id: str
    source: str  # e.g., "upload", "url", "integration"
    title: str | None = None
    url: str | None = None
    tags: list[str] = Field(default_factory=list)
    content: str
    content_hash: str
    created_at: datetime


class KBSearchRequest(BaseModel):
    """Request model for KB search."""
    query: str
    workspace_id: str
    k: int = Field(default=5, ge=1, le=50)
    with_vectors: bool = Field(default=False)  # Debug flag


class KBSearchResult(BaseModel):
    """Single search result."""
    chunk_id: str
    content: str
    score: float
    workspace_id: str
    source: str
    title: str | None = None
    url: str | None = None
    tags: list[str] = Field(default_factory=list)


class KBSearchResponse(BaseModel):
    """Response model for KB search."""
    results: list[KBSearchResult]
    query: str
    k: int
