# knowledge-base-marketplace
![CI](https://github.com/mainlayer/knowledge-base-marketplace/actions/workflows/ci.yml/badge.svg) ![License](https://img.shields.io/badge/license-MIT-blue)

RAG knowledge base marketplace — publish curated knowledge bases and sell per-query access to AI agents via Mainlayer billing.

## Install

```bash
pip install mainlayer fastapi uvicorn httpx
```

## Quickstart

```python
import httpx

# Query a knowledge base — charged per query
resp = httpx.post(
    "http://localhost:8003/knowledge-bases/kb_python_docs/query",
    headers={"x-agent-key": "your-mainlayer-token"},
    json={"query": "How to define async routes in FastAPI?", "top_k": 5},
)
result = resp.json()
print(result["context"])   # inject into your LLM prompt
print(result["payment_id"])  # Mainlayer transaction reference
```

## Features

- Pre-seeded with 3 sample knowledge bases (Python docs, legal, medical)
- Publish your own KB and set a price-per-query
- Document ingestion endpoint for populating KBs
- Mock RAG engine (swap with Qdrant/Pinecone/Chroma in production)
- Mainlayer per-query charging with 402 on payment failure

## Run locally

```bash
MAINLAYER_API_KEY=... uvicorn src.main:app --port 8003 --reload
```

📚 [mainlayer.fr](https://mainlayer.fr)
