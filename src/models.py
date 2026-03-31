"""
Pydantic models for the Knowledge Base Marketplace API.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
import uuid


# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------

class KnowledgeBasePublish(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Display name of the knowledge base")
    description: str = Field(..., min_length=1, max_length=1024)
    domain: str = Field(..., description="Domain category, e.g. 'technology', 'legal', 'medical'")
    price_per_query: float = Field(..., gt=0, description="Price in USD per RAG query")

    @validator("price_per_query")
    def round_price(cls, v: float) -> float:  # noqa: N805
        return round(v, 6)


class KnowledgeBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    domain: str
    price_per_query: float
    owner_id: str = "system"
    mainlayer_resource_id: Optional[str] = None
    document_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ---------------------------------------------------------------------------
# Documents / Ingestion
# ---------------------------------------------------------------------------

class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kb_id: str
    content: str
    source: str = "user-upload"
    metadata: dict = Field(default_factory=dict)
    embedding: Optional[List[float]] = None  # populated by vector store
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class IngestDocument(BaseModel):
    content: str = Field(..., min_length=1)
    source: str = Field(default="upload")
    metadata: dict = Field(default_factory=dict)


class IngestRequest(BaseModel):
    documents: List[IngestDocument] = Field(..., min_items=1, max_items=200)


class IngestResponse(BaseModel):
    kb_id: str
    ingested_count: int
    total_documents: int
    message: str


# ---------------------------------------------------------------------------
# RAG Query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2048)
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResult(BaseModel):
    content: str
    score: float = Field(..., description="Cosine similarity score 0-1")
    source: str
    metadata: dict = Field(default_factory=dict)


class QueryResponse(BaseModel):
    kb_id: str
    query: str
    results: List[QueryResult]
    context: str = Field(..., description="Concatenated context string for LLM injection")
    payment_id: Optional[str] = None
    tokens_charged: float = Field(default=0.005, description="USD charged for this query")


# ---------------------------------------------------------------------------
# Mainlayer / Payment
# ---------------------------------------------------------------------------

class MainlayerResource(BaseModel):
    resource_id: str
    name: str
    price: float
    currency: str = "usd"
    status: str = "active"


class PaymentVerification(BaseModel):
    payment_id: str
    amount: float
    currency: str
    status: str
    resource_id: str


# ---------------------------------------------------------------------------
# Generic API responses
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    knowledge_bases: int = 0
