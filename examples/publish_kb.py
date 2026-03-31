"""
Example: Publish a knowledge base and ingest documents.

Usage:
    MAINLAYER_API_KEY=<your-key> python examples/publish_kb.py
"""
import os
import httpx

BASE_URL = "http://localhost:8003"
API_KEY = os.getenv("MAINLAYER_API_KEY", "demo-key")


def main() -> None:
    headers = {"x-mainlayer-key": API_KEY}

    # 1. Publish the KB
    resp = httpx.post(
        f"{BASE_URL}/knowledge-bases",
        headers=headers,
        json={
            "name": "FastAPI Best Practices",
            "description": "Curated FastAPI patterns and production tips from real-world projects.",
            "domain": "technology",
            "price_per_query": 0.003,
        },
    )
    resp.raise_for_status()
    kb = resp.json()
    kb_id = kb["id"]
    print(f"Published KB: {kb_id}")
    print(f"Mainlayer resource: {kb['mainlayer_resource_id']}")

    # 2. Ingest some documents
    resp = httpx.post(
        f"{BASE_URL}/knowledge-bases/{kb_id}/ingest",
        headers=headers,
        json={
            "documents": [
                {
                    "content": "Always use Pydantic models for request/response validation in FastAPI.",
                    "source": "best-practices-guide",
                    "metadata": {"section": "validation"},
                },
                {
                    "content": "Use async def for route handlers when calling external APIs or databases.",
                    "source": "best-practices-guide",
                    "metadata": {"section": "async"},
                },
                {
                    "content": "Add dependency injection for authentication using FastAPI's Depends().",
                    "source": "best-practices-guide",
                    "metadata": {"section": "auth"},
                },
            ]
        },
    )
    resp.raise_for_status()
    ingest = resp.json()
    print(f"Ingested {ingest['ingested_count']} documents. Total: {ingest['total_documents']}")


if __name__ == "__main__":
    main()
