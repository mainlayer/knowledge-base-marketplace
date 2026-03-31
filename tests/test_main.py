"""Tests for the Knowledge Base Marketplace API."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app, _kbs


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["knowledge_bases"] >= 3  # seeded


# ---------------------------------------------------------------------------
# GET /knowledge-bases
# ---------------------------------------------------------------------------


def test_list_knowledge_bases(client):
    resp = client.get("/knowledge-bases")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3


def test_list_knowledge_bases_filter_domain(client):
    resp = client.get("/knowledge-bases", params={"domain": "technology"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(kb["domain"] == "technology" for kb in data["items"])


# ---------------------------------------------------------------------------
# POST /knowledge-bases
# ---------------------------------------------------------------------------


@patch("src.main.create_resource", new_callable=AsyncMock)
def test_publish_knowledge_base(mock_create, client):
    from src.models import MainlayerResource

    mock_create.return_value = MainlayerResource(
        resource_id="res_new_001",
        name="Test KB",
        price=0.005,
        currency="usd",
        status="active",
    )

    resp = client.post(
        "/knowledge-bases",
        json={
            "name": "Test Knowledge Base",
            "description": "A knowledge base for testing",
            "domain": "science",
            "price_per_query": 0.005,
        },
        headers={"x-mainlayer-key": "test-api-key"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Knowledge Base"
    assert data["mainlayer_resource_id"] == "res_new_001"


def test_publish_requires_key(client):
    resp = client.post(
        "/knowledge-bases",
        json={"name": "X", "description": "Y", "domain": "z", "price_per_query": 0.01},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /knowledge-bases/{id}
# ---------------------------------------------------------------------------


def test_get_kb_existing(client):
    resp = client.get("/knowledge-bases/kb_python_docs")
    assert resp.status_code == 200
    assert resp.json()["id"] == "kb_python_docs"


def test_get_kb_not_found(client):
    resp = client.get("/knowledge-bases/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /knowledge-bases/{id}/query
# ---------------------------------------------------------------------------


@patch("src.main.charge_for_query", new_callable=AsyncMock)
def test_query_kb(mock_charge, client):
    from src.models import PaymentVerification

    mock_charge.return_value = PaymentVerification(
        payment_id="pay_test_001",
        amount=0.005,
        currency="usd",
        status="captured",
        resource_id="res_python_docs",
    )

    resp = client.post(
        "/knowledge-bases/kb_python_docs/query",
        headers={"x-agent-key": "agent-token"},
        json={"query": "How to define a function?", "top_k": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kb_id"] == "kb_python_docs"
    assert data["payment_id"] == "pay_test_001"
    assert len(data["results"]) <= 3


def test_query_requires_agent_key(client):
    resp = client.post(
        "/knowledge-bases/kb_python_docs/query",
        json={"query": "test"},
    )
    assert resp.status_code == 422
