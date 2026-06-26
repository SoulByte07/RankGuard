import asyncio

from httpx import AsyncClient


async def test_create(client: AsyncClient, sample_user_id: str):
    resp = await client.post(
        "/transaction",
        json={
            "idempotency_key": "t1",
            "user_id": sample_user_id,
            "type": "earn",
            "amount": 100.50,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["idempotency_key"] == "t1"
    assert data["user_id"] == sample_user_id
    assert data["type"] == "earn"
    assert data["amount"] == 100.50


async def test_duplicate_idempotency(client: AsyncClient, sample_user_id: str):
    payload = {
        "idempotency_key": "dup",
        "user_id": sample_user_id,
        "type": "earn",
        "amount": 50,
    }
    resp1 = await client.post("/transaction", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/transaction", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["idempotency_key"] == "dup"

    summary = await client.get(f"/summary/{sample_user_id}")
    assert summary.json()["total_earned"] == 50
    assert summary.json()["transaction_count"] == 1


async def test_concurrent_same_user(client: AsyncClient, sample_user_id: str):
    async def post(i: int):
        return await client.post(
            "/transaction",
            json={
                "idempotency_key": f"concurrent-{i}",
                "user_id": sample_user_id,
                "type": "earn",
                "amount": 10,
            },
        )

    responses = await asyncio.gather(*[post(i) for i in range(10)])
    assert all(r.status_code == 201 for r in responses)

    summary = await client.get(f"/summary/{sample_user_id}")
    assert summary.json()["total_earned"] == 10 * 10


async def test_validation_errors(client: AsyncClient):
    uid = "00000000-0000-0000-0000-000000000001"

    resp = await client.post(
        "/transaction",
        json={"idempotency_key": "v1", "user_id": uid, "type": "invalid", "amount": 10},
    )
    assert resp.status_code == 422

    resp = await client.post(
        "/transaction",
        json={"idempotency_key": "v2", "user_id": uid, "type": "earn", "amount": -5},
    )
    assert resp.status_code == 422

    resp = await client.post("/transaction", json={})
    assert resp.status_code == 422
