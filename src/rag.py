"""
Mock RAG (Retrieval-Augmented Generation) query engine.

In production, replace with a real vector store (Qdrant, Pinecone, Chroma, etc.)
and an embedding model.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List

from .models import Document, KnowledgeBase, QueryResult

# In-memory vector store: kb_id -> list of Document
_document_store: Dict[str, List[Document]] = {}


def add_documents(kb_id: str, documents: List[Document]) -> None:
    """Add documents to the in-memory store for a knowledge base."""
    if kb_id not in _document_store:
        _document_store[kb_id] = []
    _document_store[kb_id].extend(documents)


def get_document_count(kb_id: str) -> int:
    return len(_document_store.get(kb_id, []))


def _cosine_sim(query: str, text: str) -> float:
    """
    Mock cosine similarity: counts word overlap.

    In production, replace with real embedding dot-product similarity.
    """
    q_words = set(query.lower().split())
    t_words = set(text.lower().split())
    overlap = len(q_words & t_words)
    if not q_words or not t_words:
        return 0.0
    return overlap / math.sqrt(len(q_words) * len(t_words))


def query_knowledge_base(
    kb_id: str,
    query: str,
    top_k: int = 5,
) -> List[QueryResult]:
    """
    Retrieve the most relevant documents for a query.

    Returns up to top_k QueryResult objects sorted by descending similarity score.
    """
    docs = _document_store.get(kb_id, [])

    if not docs:
        # Return synthetic results when no documents are ingested (demo mode)
        return _synthetic_results(query, top_k)

    scored = [
        (_cosine_sim(query, doc.content), doc)
        for doc in docs
    ]
    scored.sort(key=lambda x: x[0], reverse=True)

    results: List[QueryResult] = []
    for score, doc in scored[:top_k]:
        results.append(
            QueryResult(
                content=doc.content,
                score=round(score, 4),
                source=doc.source,
                metadata=doc.metadata,
            )
        )
    return results


def build_context(results: List[QueryResult]) -> str:
    """Concatenate result contents into a single context string for LLM injection."""
    return "\n\n---\n\n".join(r.content for r in results)


def _synthetic_results(query: str, top_k: int) -> List[QueryResult]:
    """Generate plausible synthetic results for a query (demo mode)."""
    templates = [
        f"Based on available knowledge, '{query}' relates to several key concepts in this domain.",
        f"Research indicates that '{query}' is a commonly studied topic with multiple dimensions.",
        f"Expert analysis of '{query}' suggests considering both theoretical and practical aspects.",
        f"Historical context for '{query}' shows evolving understanding over the past decade.",
        f"Recent developments in '{query}' have opened new avenues for further research.",
    ]
    results = []
    for i, template in enumerate(templates[:top_k]):
        score = round(0.95 - i * 0.08 + random.uniform(-0.02, 0.02), 4)
        results.append(
            QueryResult(
                content=template,
                score=max(0.1, min(1.0, score)),
                source="synthetic-demo",
                metadata={"rank": i + 1},
            )
        )
    return results
