from httpx import AsyncClient


async def test_ranking_order(client: AsyncClient, sample_user_id: str, other_user_id: str):
    await client.post(
        "/transaction",
        json={
            "idempotency_key": "r1",
            "user_id": sample_user_id,
            "type": "earn",
            "amount": 200,
        },
    )
    await client.post(
        "/transaction",
        json={
            "idempotency_key": "r2",
            "user_id": other_user_id,
            "type": "earn",
            "amount": 100,
        },
    )

    resp = await client.get("/ranking?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 2
    assert data["results"][0]["user_id"] == sample_user_id
    assert data["results"][0]["rank"] == 1
    assert data["results"][1]["rank"] == 2


async def test_pagination(client: AsyncClient, sample_user_id: str, other_user_id: str):
    await client.post(
        "/transaction",
        json={
            "idempotency_key": "p1",
            "user_id": sample_user_id,
            "type": "earn",
            "amount": 100,
        },
    )
    await client.post(
        "/transaction",
        json={
            "idempotency_key": "p2",
            "user_id": other_user_id,
            "type": "earn",
            "amount": 100,
        },
    )

    resp = await client.get("/ranking?limit=1&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 1

    resp = await client.get("/ranking?limit=1&offset=1")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 1

    resp = await client.get("/ranking?limit=1&offset=99")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 0
