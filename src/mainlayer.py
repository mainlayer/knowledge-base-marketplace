"""
Mainlayer payment integration for the Knowledge Base Marketplace.

Mainlayer is "Stripe for AI agents" — it handles metered billing for
resource access.  Every paid RAG query is verified through a Mainlayer
payment before results are returned.

Docs: https://api.mainlayer.fr
Auth: Authorization: Bearer <MAINLAYER_API_KEY>
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx
from fastapi import HTTPException, status

from .models import MainlayerResource, PaymentVerification

logger = logging.getLogger(__name__)

MAINLAYER_BASE_URL = os.getenv("MAINLAYER_BASE_URL", "https://api.mainlayer.fr")
MAINLAYER_API_KEY = os.getenv("MAINLAYER_API_KEY", "")

# Default request timeout (seconds)
_TIMEOUT = 10.0


def _headers() -> dict[str, str]:
    if not MAINLAYER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MAINLAYER_API_KEY is not configured on this server.",
        )
    return {
        "Authorization": f"Bearer {MAINLAYER_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "knowledge-base-marketplace/1.0",
    }


# ---------------------------------------------------------------------------
# Resource management
# ---------------------------------------------------------------------------

async def create_resource(
    name: str,
    description: str,
    price_per_query: float,
    kb_id: str,
) -> MainlayerResource:
    """Register a knowledge base as a paid Mainlayer resource."""
    payload = {
        "name": name,
        "description": description,
        "price": price_per_query,
        "currency": "usd",
        "metadata": {
            "kb_id": kb_id,
            "type": "knowledge-base-query",
        },
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{MAINLAYER_BASE_URL}/resources",
                json=payload,
                headers=_headers(),
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Mainlayer create_resource failed: %s", exc.response.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Mainlayer error: {exc.response.text}",
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Mainlayer unreachable: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not reach Mainlayer API.",
            ) from exc

    data = resp.json()
    return MainlayerResource(
        resource_id=data.get("id") or data.get("resource_id", ""),
        name=data.get("name", name),
        price=data.get("price", price_per_query),
        currency=data.get("currency", "usd"),
        status=data.get("status", "active"),
    )


async def get_resource(resource_id: str) -> Optional[MainlayerResource]:
    """Retrieve a resource from Mainlayer."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.get(
                f"{MAINLAYER_BASE_URL}/resources/{resource_id}",
                headers=_headers(),
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Mainlayer get_resource failed: %s", exc.response.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Mainlayer error: {exc.response.text}",
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Mainlayer unreachable: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not reach Mainlayer API.",
            ) from exc

    data = resp.json()
    return MainlayerResource(
        resource_id=data.get("id") or data.get("resource_id", resource_id),
        name=data.get("name", ""),
        price=data.get("price", 0.0),
        currency=data.get("currency", "usd"),
        status=data.get("status", "active"),
    )


# ---------------------------------------------------------------------------
# Payment / charge
# ---------------------------------------------------------------------------

async def charge_for_query(
    resource_id: str,
    amount: float,
    agent_api_key: str,
    kb_id: str,
    query_preview: str,
) -> PaymentVerification:
    """
    Charge an AI agent for a single RAG query.

    The agent passes its own Mainlayer API key (X-Agent-Key header) so
    Mainlayer can debit their account and credit the KB publisher.
    """
    payload = {
        "resource_id": resource_id,
        "amount": amount,
        "currency": "usd",
        "metadata": {
            "kb_id": kb_id,
            "query_preview": query_preview[:120],
        },
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{MAINLAYER_BASE_URL}/payments",
                json=payload,
                headers={
                    **_headers(),
                    "X-Agent-Key": agent_api_key,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("Payment rejected by Mainlayer: %s", exc.response.text)
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Payment failed: {exc.response.text}",
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Mainlayer unreachable during charge: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not reach Mainlayer payment API.",
            ) from exc

    data = resp.json()
    return PaymentVerification(
        payment_id=data.get("id") or data.get("payment_id", ""),
        amount=data.get("amount", amount),
        currency=data.get("currency", "usd"),
        status=data.get("status", "captured"),
        resource_id=resource_id,
    )


async def verify_payment(payment_id: str) -> PaymentVerification:
    """Retrieve and verify a payment record from Mainlayer."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.get(
                f"{MAINLAYER_BASE_URL}/payments/{payment_id}",
                headers=_headers(),
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Mainlayer verify_payment failed: %s", exc.response.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Mainlayer error: {exc.response.text}",
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Mainlayer unreachable: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not reach Mainlayer API.",
            ) from exc

    data = resp.json()
    return PaymentVerification(
        payment_id=data.get("id") or data.get("payment_id", payment_id),
        amount=data.get("amount", 0.0),
        currency=data.get("currency", "usd"),
        status=data.get("status", ""),
        resource_id=data.get("resource_id", ""),
    )
