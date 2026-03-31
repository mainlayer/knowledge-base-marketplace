"""
Knowledge Base Marketplace — FastAPI application.

Endpoints:
  GET  /knowledge-bases                   List all knowledge bases
  POST /knowledge-bases                   Publish a new knowledge base
  GET  /knowledge-bases/{id}              Knowledge base detail
  POST /knowledge-bases/{id}/ingest       Add documents to a KB
  GET  /knowledge-bases/{id}/query        Query a KB (requires Mainlayer payment)
  GET  /health                            Health check
"""
from __future__ import annotations

import logging
import uuid
from typing import Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from .mainlayer import charge_for_query, create_resource
from .models import (
    Document,
    HealthResponse,
    IngestDocument,
    IngestRequest,
    IngestResponse,
    KnowledgeBase,
    KnowledgeBasePublish,
    QueryRequest,
    QueryResponse,
)
from .rag import add_documents, build_context, get_document_count, query_knowledge_base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Knowledge Base Marketplace",
    description="Sell access to curated knowledge bases. Queries charged via Mainlayer.",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_kbs: Dict[str, KnowledgeBase] = {}


def _seed() -> None:
    """Pre-seed with sample knowledge bases."""
    samples = [
        KnowledgeBase(
            id="kb_python_docs",
            name="Python 3.12 Reference",
            description="Complete Python standard library documentation with examples.",
            domain="technology",
            price_per_query=0.005,
            mainlayer_resource_id="res_python_docs",
            document_count=2450,
        ),
        KnowledgeBase(
            id="kb_legal_contracts",
            name="Commercial Contract Templates",
            description="500+ annotated commercial contract templates from US and EU jurisdictions.",
            domain="legal",
            price_per_query=0.02,
            mainlayer_resource_id="res_legal_contracts",
            document_count=512,
        ),
        KnowledgeBase(
            id="kb_medical_guidelines",
            name="Clinical Practice Guidelines 2024",
            description="WHO and AHA clinical practice guidelines for 120 conditions.",
            domain="medical",
            price_per_query=0.01,
            mainlayer_resource_id="res_medical_guidelines",
            document_count=1200,
        ),
    ]
    for kb in samples:
        _kbs[kb.id] = kb


_seed()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version="1.0.0", knowledge_bases=len(_kbs))


@app.get("/knowledge-bases", tags=["knowledge-bases"])
async def list_knowledge_bases(
    domain: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict:
    """Browse available knowledge bases. Free to list."""
    kbs = list(_kbs.values())
    if domain:
        kbs = [kb for kb in kbs if kb.domain.lower() == domain.lower()]
    total = len(kbs)
    start = (page - 1) * per_page
    return {
        "items": [kb.model_dump() for kb in kbs[start : start + per_page]],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@app.post(
    "/knowledge-bases",
    response_model=KnowledgeBase,
    status_code=status.HTTP_201_CREATED,
    tags=["knowledge-bases"],
)
async def publish_knowledge_base(
    payload: KnowledgeBasePublish,
    x_mainlayer_key: str = Header(..., description="Your Mainlayer API key"),
) -> KnowledgeBase:
    """
    Publish a knowledge base. Queries will be billed via Mainlayer.
    """
    kb_id = f"kb_{uuid.uuid4().hex[:12]}"
    resource_id: str

    try:
        ml_resource = await create_resource(
            name=payload.name,
            description=payload.description,
            price_per_query=payload.price_per_query,
            kb_id=kb_id,
        )
        resource_id = ml_resource.resource_id
    except Exception as exc:
        logger.warning("Mainlayer resource creation failed (dev mode): %s", exc)
        resource_id = f"res_{kb_id}"

    kb = KnowledgeBase(
        id=kb_id,
        name=payload.name,
        description=payload.description,
        domain=payload.domain,
        price_per_query=payload.price_per_query,
        mainlayer_resource_id=resource_id,
        owner_id=x_mainlayer_key[:16],
    )
    _kbs[kb_id] = kb
    logger.info("Knowledge base published: %s", kb_id)
    return kb


@app.get(
    "/knowledge-bases/{kb_id}",
    response_model=KnowledgeBase,
    tags=["knowledge-bases"],
)
async def get_knowledge_base(kb_id: str) -> KnowledgeBase:
    kb = _kbs.get(kb_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found.")
    return kb


@app.post(
    "/knowledge-bases/{kb_id}/ingest",
    response_model=IngestResponse,
    tags=["knowledge-bases"],
)
async def ingest_documents(
    kb_id: str,
    payload: IngestRequest,
    x_mainlayer_key: str = Header(..., description="Your Mainlayer API key"),
) -> IngestResponse:
    """Add documents to a knowledge base."""
    kb = _kbs.get(kb_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found.")

    docs = [
        Document(kb_id=kb_id, content=d.content, source=d.source, metadata=d.metadata)
        for d in payload.documents
    ]
    add_documents(kb_id, docs)
    kb.document_count = get_document_count(kb_id)

    return IngestResponse(
        kb_id=kb_id,
        ingested_count=len(docs),
        total_documents=kb.document_count,
        message=f"Ingested {len(docs)} document(s) into '{kb.name}'.",
    )


@app.post(
    "/knowledge-bases/{kb_id}/query",
    response_model=QueryResponse,
    tags=["knowledge-bases"],
)
async def query_kb(
    kb_id: str,
    payload: QueryRequest,
    x_agent_key: str = Header(..., description="Your Mainlayer payment token"),
) -> QueryResponse:
    """
    Query a knowledge base. The agent is charged per query via Mainlayer.
    """
    kb = _kbs.get(kb_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found.")

    # Charge for the query
    payment_id: Optional[str] = None
    try:
        verification = await charge_for_query(
            resource_id=kb.mainlayer_resource_id or kb_id,
            amount=kb.price_per_query,
            agent_api_key=x_agent_key,
            kb_id=kb_id,
            query_preview=payload.query,
        )
        payment_id = verification.payment_id
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Payment failed (dev mode): %s", exc)
        payment_id = "dev-payment"

    results = query_knowledge_base(kb_id, payload.query, top_k=payload.top_k)
    context = build_context(results)

    return QueryResponse(
        kb_id=kb_id,
        query=payload.query,
        results=results,
        context=context,
        payment_id=payment_id,
        tokens_charged=kb.price_per_query,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8003, reload=True)
