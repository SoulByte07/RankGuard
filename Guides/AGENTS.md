# RankGuard — AGENTS.md

**Start here.** This repo is a greenfield implementation of the assignment described in `Guides/PLAN.md`. Read that first for full context.

## Current State

- No code exists yet — everything is blueprint in `Guides/PLAN.md`
- `README.md` is a placeholder ("hello!"); update it when implementation is done
- Git remote: `git@github.com:SoulByte07/RankGuard.git` (branch `main`)
- Do not commit unless explicitly asked

## Architecture (non-obvious from filenames)

- **`user_snapshots` table**: Materialised per-user summary row updated atomically in the same DB transaction as the transaction insert. Avoids expensive `SUM/COUNT` on every read. Uses `SELECT ... FOR UPDATE` for concurrent safety.
- **Idempotency**: Client-generated `idempotency_key` with DB-level `UNIQUE` constraint. On conflict → return 200 with existing record (do not double-process).
- **Ranking**: Multi-factor formula — `(total_earned × 1.0) + (total_spent × 0.5) + (transaction_count × 10) + (bonus_count × 50) - (days_since_last_activity × 0.1)`. Computed server-side only; no client influence.
- **Ranking cache**: Materialised `rankings` table refreshed by a background task (not computed live on every GET).

## Implementation Order (from PLAN.md)

1. Scaffolding, config, DB connection
2. SQLAlchemy models + Alembic migration
3. `POST /transaction` (idempotency, validation, concurrency)
4. `GET /summary/{userId}`
5. `GET /ranking` + ranking computation
6. Ranking refresh (background task)
7. Concurrency tests
8. Frontend (vanilla HTML/CSS/JS served by FastAPI static mount)
9. Docker Compose
10. README

## Conventions

- **Async throughout**: FastAPI async handlers, SQLAlchemy async sessions, asyncpg driver
- **Validation**: Pydantic schemas for all request/response models; `400` for business rule violations, `422` for schema validation
- **DB errors**: Raise `HTTPException` from service layer; don't leak internals
- **Amounts**: Use `Decimal(12,2)` in DB (not float, not integer cents — per PLAN.md trade-off)
- **UUIDs**: `uuid.uuid4()` for all PKs and idempotency keys
- **Types**: Keep `app/` package clean; routers thin (call services), services contain business logic

## Testing

- Framework: `pytest` with `httpx.AsyncClient` for async FastAPI tests
- Key tests to write (per PLAN.md):
  - Happy path `POST /transaction` → 201
  - Same `idempotency_key` → 200 (duplicate), no double-count
  - 10 parallel requests for same user → correct final balance
  - Validation errors → 4xx
  - `GET /summary` nonexistent user → 404
  - Ranking order and pagination
- Integration: use a test DB (separate PostgreSQL or SQLite in-memory)

## Expected Commands

(Not wired yet — install and run after implementation begins)

```bash
pip install -r requirements.txt          # install deps
alembic upgrade head                     # run migrations
uvicorn app.main:app --reload            # dev server
pytest -v --asyncio-mode=auto            # run all tests
docker compose up --build                # full stack
```

## Key Files to Know

| File | Purpose |
|------|---------|
| `Guides/PLAN.md` | Full design doc — read first |
| `app/main.py` | FastAPI entrypoint, startup/shutdown, static mount |
| `app/models.py` | SQLAlchemy ORM models (users, transactions, user_snapshots, rankings) |
| `app/schemas.py` | Pydantic request/response schemas |
| `app/services/transaction.py` | Core write logic (idempotency check, atomic insert+snapshot update) |
| `app/services/ranking.py` | Score computation + materialisation |
