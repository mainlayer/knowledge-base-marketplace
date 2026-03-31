"""
Example: Query a knowledge base with Mainlayer payment.

Usage:
    MAINLAYER_TOKEN=<your-token> python examples/query_kb.py
"""
import os
import httpx

BASE_URL = "http://localhost:8003"
TOKEN = os.getenv("MAINLAYER_TOKEN", "demo-token")


def main() -> None:
    # List knowledge bases
    resp = httpx.get(f"{BASE_URL}/knowledge-bases")
    resp.raise_for_status()
    kbs = resp.json()["items"]
    print(f"Available knowledge bases: {len(kbs)}\n")
    for kb in kbs:
        print(f"[{kb['id']}] {kb['name']} — ${kb['price_per_query']}/query")

    if not kbs:
        print("No knowledge bases available.")
        return

    # Query the first one
    kb_id = kbs[0]["id"]
    print(f"\nQuerying '{kbs[0]['name']}'...")

    resp = httpx.post(
        f"{BASE_URL}/knowledge-bases/{kb_id}/query",
        headers={"x-agent-key": TOKEN},
        json={"query": "What are the main features?", "top_k": 3},
    )
    if resp.status_code == 402:
        print("Payment required. Top up your Mainlayer balance at https://mainlayer.fr")
        return
    resp.raise_for_status()

    result = resp.json()
    print(f"Payment ID: {result['payment_id']}")
    print(f"Charged: ${result['tokens_charged']}")
    print(f"\nTop {len(result['results'])} results:")
    for i, r in enumerate(result["results"], 1):
        print(f"  {i}. [score={r['score']:.3f}] {r['content'][:100]}...")


if __name__ == "__main__":
    main()
