from httpx import AsyncClient


async def test_existing_user(client: AsyncClient, sample_user_id: str):
    await client.post(
        "/transaction",
        json={
            "idempotency_key": "s1",
            "user_id": sample_user_id,
            "type": "earn",
            "amount": 100,
        },
    )

    resp = await client.get(f"/summary/{sample_user_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == sample_user_id
    assert data["total_earned"] == 100
    assert data["transaction_count"] == 1


async def test_nonexistent_user(client: AsyncClient):
    resp = await client.get("/summary/00000000-0000-0000-0000-000000000099")
    assert resp.status_code == 404
