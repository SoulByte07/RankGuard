# RankGuard

An async FastAPI backend for idempotent transaction processing, user summaries, and a multi-factor ranking leaderboard.

## Features

- **Idempotent transactions** — Client-provided `idempotency_key` guarantees exactly-once processing; duplicates return the existing record (200) instead of double-counting.
- **Atomic snapshot updates** — Per-user materialised summary rows (`total_earned`, `total_spent`, `net_balance`, etc.) are updated in the same DB transaction as the transaction insert via `SELECT ... FOR UPDATE`.
- **Multi-factor ranking** — `score = earned × 1.0 + spent × 0.5 + tx_count × 10 + bonus_count × 50 − days_since_activity × 0.1`. Stored in a materialised `rankings` table; can be refreshed on demand.
- **Concurrency-safe** — Per-user `asyncio.Lock` serialises concurrent requests for the same user; idempotency key uniqueness is enforced at the DB level.
- **Rate limiting** — Configurable per-IP sliding window middleware.
- **Async throughout** — FastAPI async handlers, SQLAlchemy 2.0 async sessions, asyncpg driver.

## Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.11+ / FastAPI |
| Database | PostgreSQL 16 (prod) / SQLite (dev/test) |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Testing | pytest + httpx.AsyncClient |
| Deploy | Docker Compose |

## Quick start

```bash
git clone https://github.com/SoulByte07/RankGuard.git
cd RankGuard
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rankgward
RATE_LIMIT_MAX_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
```

Run with Docker Compose:

```bash
docker compose up --build
```

Or run directly (requires a running PostgreSQL):

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API

### `POST /transaction`
Create a transaction. Returns **201** on first write, **200** on duplicate idempotency key.

```json
{
  "idempotency_key": "client-generated-unique-key",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "type": "earn | spend | bonus",
  "amount": 100.50,
  "extra_data": {}
}
```

### `GET /summary/{user_id}`
Get a user's aggregated summary and ranking position.

### `GET /ranking?limit=50&offset=0`
Get the leaderboard, ordered by score descending (and last activity ascending as tiebreaker).

### `POST /ranking/compute`
Force-refresh the materialised ranking table. Rankings are automatically computed on the first `GET /ranking` if empty.

### `GET /health`
Health check.

## Project structure

```
app/
├── main.py                 # FastAPI entrypoint, middleware, router registration
├── config.py               # Pydantic settings (env-driven)
├── database.py             # Async engine + session factory
├── models.py               # SQLAlchemy ORM models (4 tables)
├── schemas.py              # Pydantic request/response models
├── middlewares/
│   └── rate_limit.py       # Per-IP sliding window rate limiter
├── routers/
│   ├── transaction.py      # POST /transaction
│   ├── summary.py          # GET /summary/{user_id}
│   └── ranking.py          # GET /ranking, POST /ranking/compute
└── services/
    ├── transaction.py      # Core write logic (idempotency, snapshot)
    ├── summary.py          # Snapshot + rank lookup
    └── ranking.py          # Ranking formula, compute, pagination
tests/
├── conftest.py             # Fixtures (SQLite in-memory, async client)
├── test_transaction.py     # Create, duplicate, concurrent, validation
├── test_summary.py         # Existing/nonexistent user
└── test_ranking.py         # Ordering and pagination
```

## Testing

```bash
pytest -v --asyncio-mode=auto
```

Tests use an in-memory SQLite database via `aiosqlite` — no external dependencies required.

## License

MIT
