# Knowledge Base Marketplace

![CI](https://github.com/mainlayer/knowledge-base-marketplace/actions/workflows/ci.yml/badge.svg) ![License](https://img.shields.io/badge/license-MIT-blue)

RAG knowledge base marketplace powered by Mainlayer. Publish curated knowledge bases and charge agents per-query access via secure payments.

## Overview

This template demonstrates a production-ready knowledge base marketplace where:

- **Publishers** create and upload knowledge bases on specialized topics (Python docs, legal contracts, medical guidelines, etc.)
- **Agents** browse available KBs and query them on-demand
- **Mainlayer** charges per-query, enabling micro-transactions and pay-as-you-go pricing
- **RAG Integration** provides semantic search and context injection for LLMs

## Installation

```bash
pip install mainlayer fastapi uvicorn httpx aiohttp tenacity pydantic
```

## Quick Start

### 1. Set your Mainlayer API key

```bash
export MAINLAYER_API_KEY="sk_..."
uvicorn src.main:app --port 8003 --reload
```

### 2. Browse available knowledge bases

```bash
curl http://localhost:8003/knowledge-bases
```

Response:

```json
{
  "items": [
    {
      "id": "kb_python_docs",
      "name": "Python 3.12 Reference",
      "description": "Complete Python standard library documentation",
      "domain": "technology",
      "price_per_query": 0.005,
      "document_count": 2450
    },
    {
      "id": "kb_legal_contracts",
      "name": "Commercial Contract Templates",
      "description": "500+ annotated commercial contract templates",
      "domain": "legal",
      "price_per_query": 0.02,
      "document_count": 512
    }
  ],
  "total": 3,
  "page": 1
}
```

### 3. Query a knowledge base (charged per query)

```bash
curl -X POST http://localhost:8003/knowledge-bases/kb_python_docs/query \
  -H "Content-Type: application/json" \
  -H "x-agent-key: sk_agent_..." \
  -d '{
    "query": "How to define async routes in FastAPI?",
    "top_k": 5
  }'
```

Response:

```json
{
  "kb_id": "kb_python_docs",
  "query": "How to define async routes in FastAPI?",
  "results": [
    {
      "source": "fastapi_docs.md",
      "content": "Use async def to define async routes...",
      "relevance": 0.95
    }
  ],
  "context": "Use async def to define async routes in FastAPI...",
  "payment_id": "pay_...",
  "tokens_charged": 0.005
}
```

### 4. Publish your own knowledge base

```bash
curl -X POST http://localhost:8003/knowledge-bases \
  -H "Content-Type: application/json" \
  -H "x-mainlayer-key: sk_..." \
  -d '{
    "name": "React Patterns Guide",
    "description": "Comprehensive guide to React design patterns and best practices",
    "domain": "technology",
    "price_per_query": 0.01
  }'
```

### 5. Ingest documents into your KB

```bash
curl -X POST http://localhost:8003/knowledge-bases/kb_react_guide/ingest \
  -H "Content-Type: application/json" \
  -H "x-mainlayer-key: sk_..." \
  -d '{
    "documents": [
      {
        "content": "The Context API allows you to pass data...",
        "source": "react_context_api.md",
        "metadata": {"chapter": 3}
      },
      {
        "content": "Hooks let you use state without writing a class...",
        "source": "react_hooks.md",
        "metadata": {"chapter": 4}
      }
    ]
  }'
```

## API Endpoints

### Knowledge Bases

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/knowledge-bases` | List all KBs (filterable by domain) |
| `POST` | `/knowledge-bases` | Publish a new KB |
| `GET` | `/knowledge-bases/{id}` | Get KB details |
| `POST` | `/knowledge-bases/{id}/ingest` | Add documents to a KB |
| `POST` | `/knowledge-bases/{id}/query` | Query a KB (charged per query) |

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check & stats |

## Features

- **Pre-seeded KBs**: Python docs, legal contracts, medical guidelines included
- **Flexible Pricing**: Set any price-per-query for your KB
- **Semantic Search**: RAG-based document retrieval
- **Per-Query Billing**: Charge micro-transactions via Mainlayer
- **Document Ingestion**: Bulk upload documents with metadata
- **Domain Filtering**: Organize KBs by domain (technology, legal, medical, etc.)
- **Scalable Backend**: Async FastAPI for high-concurrency querying
- **Payment Verification**: 402 responses when agents lack funds

## Architecture

```
Agent (GET /knowledge-bases)
        ↓
Browse available KBs
        ↓
Agent (POST /knowledge-bases/{id}/query with payment token)
        ↓
Mainlayer verifies funds and charges per-query fee
        ↓
RAG Engine retrieves relevant documents
        ↓
Return context + payment reference to agent
        ↓
Agent injects context into LLM prompt
```

## RAG Integration

Replace the mock RAG engine with production systems:

- **Qdrant**: Managed vector DB with semantic search
- **Pinecone**: Serverless vector database
- **Chroma**: Open-source embedding database
- **Weaviate**: GraphQL-powered vector search
- **Milvus**: Scalable distributed vector store

```python
# src/rag.py — integrate your preferred vector store
from qdrant_client import QdrantClient

client = QdrantClient("localhost", port=6333)

def query_knowledge_base(kb_id: str, query: str, top_k: int = 5):
    # Search vectors for semantic similarity
    results = client.search(
        collection_name=kb_id,
        query_vector=embed(query),
        limit=top_k,
    )
    return results
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/

# Format
ruff format src/
```

## Production Deployment

1. Replace mock RAG with Qdrant/Pinecone/Weaviate
2. Use PostgreSQL for KB metadata and access logs
3. Implement async document processing pipeline
4. Add webhook handlers for payment confirmation
5. Configure rate limiting per agent/KB
6. Set up query result caching (Redis)
7. Implement usage analytics and billing reports
8. Add content moderation and compliance checks

## Pricing Strategies

- **Freemium**: Free KBs + premium paid KBs
- **Tiered**: Different price-per-query based on KB quality
- **Volume Discounts**: Bulk query discounts for agents
- **Subscription**: Unlimited queries for subscription agents

## Support

- Docs: [mainlayer.fr](https://mainlayer.fr)
- Issues: [GitHub Issues](https://github.com/mainlayer/knowledge-base-marketplace/issues)
