# RankGuard — Implementation Plan

## 1. Overview

**RankGuard** is a backend service + live frontend that manages user transactions, per-user summary statistics, and a fair multi-factor ranking leaderboard. It demonstrates strong API design, data consistency, concurrency handling, duplicate prevention, and basic abuse protection.

---

## 2. Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.11+ | Required |
| Web Framework | **FastAPI** | Async, auto-docs, pydantic validation, fast |
| Database | **PostgreSQL** (via `asyncpg` / SQLAlchemy async) | Real persistence, row-level locking, unique constraints |
| Migrations | **Alembic** | Schema versioning |
| Frontend | **Vanilla JS + HTML + CSS** (served via FastAPI static files) | Zero build step, deployable as a single unit |
| Async Task / Lock | **Redis** (optional, for distributed rate-limiting) or **in-process asyncio.Lock** | For idempotency keys and concurrency |
| Testing | **pytest + httpx** (async) | Coverage for concurrency, validation, ranking |
| Deployment | **Docker Compose** (app + postgres + optional redis) | Portable, reproducible |

### Fallback (if PostgreSQL/Redis is too heavy)

- SQLite (with WAL mode) for persistence
- In-memory dict with `asyncio.Lock` for idempotency
- Document trade-offs clearly

---

## 3. Project Structure

```
rankguard/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, startup, shutdown, static mount
│   ├── config.py                # Settings via pydantic-settings / env vars
│   ├── database.py              # Async engine, sessionmaker
│   ├── models.py                # SQLAlchemy ORM models
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── transaction.py       # POST /transaction
│   │   ├── summary.py           # GET /summary/{userId}
│   │   └── ranking.py           # GET /ranking
│   ├── services/
│   │   ├── __init__.py
│   │   ├── transaction.py       # Business logic, duplicate check, validation
│   │   ├── summary.py           # Summary aggregation logic
│   │   └── ranking.py           # Multi-factor ranking computation
│   ├── middlewares/
│   │   ├── __init__.py
│   │   └── rate_limit.py        # Optional: per-IP rate limiting
│   └── static/
│       ├── index.html
│       ├── app.js
│       └── style.css
├── alembic/
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_transaction.py
│   ├── test_summary.py
│   └── test_ranking.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
└── README.md
```

---

## 4. Database Schema

### Table: `users`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| created_at | TIMESTAMP | NOT NULL, default now() |

### Table: `transactions`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| user_id | UUID | FK → users.id, NOT NULL, indexed |
| idempotency_key | VARCHAR(255) | UNIQUE, NOT NULL — **prevents duplicates** |
| type | ENUM('earn', 'spend', 'bonus') | NOT NULL |
| amount | DECIMAL(12,2) | NOT NULL, > 0 |
| metadata | JSONB | Nullable, arbitrary payload |
| created_at | TIMESTAMP | NOT NULL, default now() |

> **Why idempotency_key?** The client generates a unique key per intent. If a request arrives with a key already in the DB, we return the existing transaction (idempotent success) instead of processing a duplicate. The UNIQUE constraint guarantees this at the database level — the safest anti-duplicate mechanism.

### Table: `user_snapshots` (materialised summary, updated via transaction trigger)

| Column | Type | Constraints |
|--------|------|-------------|
| user_id | UUID | PK, FK → users.id |
| total_earned | DECIMAL(12,2) | NOT NULL, default 0 |
| total_spent | DECIMAL(12,2) | NOT NULL, default 0 |
| net_balance | DECIMAL(12,2) | NOT NULL, default 0 |
| transaction_count | INTEGER | NOT NULL, default 0 |
| last_activity | TIMESTAMP | NOT NULL, default now() |
| bonus_count | INTEGER | NOT NULL, default 0 |
| updated_at | TIMESTAMP | NOT NULL, default now() |

> **Why a separate snapshot table?** Reading `SUM/COUNT` over transactions on every `/summary` and `/ranking` call does not scale. We maintain a materialised row per user that is updated **in the same database transaction** as the insert. This gives us consistent reads without locks on the transaction table.

### Table: `rankings` (refreshed periodically or on-demand)

| Column | Type | Constraints |
|--------|------|-------------|
| user_id | UUID | PK, FK → users.id |
| score | DECIMAL(12,2) | Computed rank score |
| rank | INTEGER | Position (1 = highest) |
| computed_at | TIMESTAMP | NOT NULL, default now() |

> Either a materialised table refreshed via a background task or a `CREATE MATERIALIZED VIEW` (PostgreSQL). The ranking query itself is simple enough but expensive over many users; caching avoids O(n) scans on every GET.

---

## 5. API Design

### 5.1 `POST /transaction`

**Request:**
```json
{
  "idempotency_key": "client-generated-uuid-v4",
  "user_id": "uuid",
  "type": "earn | spend | bonus",
  "amount": 100.50,
  "metadata": { "description": "Task completion bonus" }
}
```

**Responses:**
- `201 Created` — new transaction processed
- `200 OK` — duplicate (same idempotency_key already processed, return existing)
- `400 Bad Request` — validation failure (negative amount, missing fields, bad type)
- `409 Conflict` — concurrent attempt detected (optimistic lock / advisory lock)
- `422 Unprocessable` — pydantic schema validation

**Validation rules:**
- `idempotency_key`: required, non-empty, max 255 chars
- `user_id`: required, valid UUID
- `type`: one of `earn`, `spend`, `bonus`
- `amount`: required, > 0, max 2 decimal places (or integer cents)
- `metadata`: optional dict

**Concurrency handling:**
1. `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING` — single atomic statement.
2. Wrap the insert + snapshot update in a DB transaction.
3. `SELECT ... FOR UPDATE` on the `user_snapshots` row to prevent concurrent updates to the same user's balance.

**Duplicate detection flow:**
```
1. Validate request body → pydantic
2. BEGIN
3. Try INSERT into transactions (idempotency_key is UNIQUE)
   a. If success → update user_snapshots (atomic)
   b. If conflict → SELECT existing transaction → RETURN 200
4. COMMIT
```

### 5.2 `GET /summary/{userId}`

**Response:**
```json
{
  "user_id": "uuid",
  "total_earned": 1500.00,
  "total_spent": 200.00,
  "net_balance": 1300.00,
  "transaction_count": 42,
  "bonus_count": 5,
  "rank": 7,
  "last_activity": "2026-06-24T12:00:00Z"
}
```

- `404 Not Found` — userId does not exist
- Returns data from `user_snapshots` + rank from `rankings` table

### 5.3 `GET /ranking`

**Query params:**
- `limit` (int, default 50, max 200)
- `offset` (int, default 0)

**Response:**
```json
{
  "count": 1000,
  "results": [
    {
      "rank": 1,
      "user_id": "uuid",
      "score": 2540.50,
      "total_earned": 3000.00,
      "total_spent": 459.50,
      "transaction_count": 120
    }
  ]
}
```

---

## 6. Ranking Algorithm (Multi-Factor)

The ranking score balances **activity volume**, **value contribution**, and **consistency**.

```
score = (total_earned × 1.0)
      + (total_spent × 0.5)         → spending also shows engagement
      + (transaction_count × 10)    → bonus for frequency
      + (bonus_count × 50)          → bonus tasks weighted higher
      - (age_penalty)               → decay if old last_activity
```

**Age penalty:** `(days_since_last_activity) × 0.1` — prevents stale accounts from staying at the top.

This ensures:
- High earners rank well
- Frequent small transactions also accumulate value via `transaction_count`
- Bonus achievements are rewarded disproportionately
- Inactive users decay naturally

**Tiebreaker:** `last_activity ASC` (earlier adopter ranks higher on tie).

---

## 7. Anti-Abuse / Manipulation Prevention

| Concern | Mitigation |
|---------|-----------|
| Duplicate requests | `idempotency_key` with DB UNIQUE constraint |
| Concurrent balance updates | `SELECT ... FOR UPDATE` on user_snapshot row |
| Rapid-fire requests | Rate limiting per IP (middleware) |
| Negative amounts | Server-side validation, reject |
| Spoofing other users | Validate `user_id` exists, return 404 if not |
| Excessive transaction types | Enum constraint at DB + pydantic level |
| Ranking manipulation | Score is computed server-side; no client input affects it beyond valid transaction data |
| Race condition: read-then-write | Use atomic `UPDATE user_snapshots SET ... WHERE user_id = ... RETURNING ...` instead of read + compute + write |

---

## 8. Frontend (Live Demo)

**Pages:**
1. **Dashboard** — form to submit a transaction (user_id, type, amount, optional description). Shows the created transaction response.
2. **User Summary** — input user_id, fetch and display summary with rank.
3. **Leaderboard** — table of top N users with score breakdown.
4. **Auto-refresh** — leaderboard polls every 10 seconds.

**Tech:** Vanilla HTML/CSS/JS served by FastAPI static file mount. No build step.

---

## 9. Implementation Order

| Step | What | Why first |
|------|------|-----------|
| 1 | Project scaffolding, config, database connection | Foundation |
| 2 | Models + Alembic migration | Schema must exist before APIs |
| 3 | `POST /transaction` with idempotency + validation | Core write path |
| 4 | `GET /summary/{userId}` | Core read path |
| 5 | `GET /ranking` with multi-factor score | Core read path |
| 6 | Ranking materialisation (cron / refresh endpoint) | Performance for step 5 |
| 7 | Concurrency tests | Verify correctness under load |
| 8 | Frontend | Visual demonstration |
| 9 | Docker Compose | One-command deploy |
| 10 | README | Documentation |

---

## 10. Testing Strategy

| Test | What it covers |
|------|----------------|
| `test_transaction_create` | Happy path POST → 201 |
| `test_transaction_duplicate` | Same idempotency_key → 200, no double-count |
| `test_transaction_concurrent_same_user` | 10 parallel requests for same user → correct final balance |
| `test_transaction_validation` | Missing fields, bad types, negative amounts → 4xx |
| `test_summary_nonexistent_user` | 404 |
| `test_summary_after_transactions` | Verify snapshot matches inserts |
| `test_ranking_order` | Users with higher scores appear first |
| `test_ranking_limit_offset` | Pagination |

---

## 11. Trade-offs & Limitations

| Choice | Trade-off |
|--------|-----------|
| Materialised `user_snapshots` | Extra write on every transaction, but O(1) reads |
| Ranking cache | Stale by up to `N` seconds; acceptable for leaderboard |
| In-process lock vs distributed | If scaled to multiple app instances, need Redis |
| Idempotency key in application | Client must generate and retry properly; documented in README |
| SQLite fallback | No `SELECT FOR UPDATE`, less concurrency safety |
| Integer cents vs DECIMAL | Using DECIMAL to keep it readable, but integer cents avoid floating-point issues |

---

## 12. Future Considerations (Out of Scope)

- WebSocket push for live leaderboard updates
- Admin API to void transactions
- Authentication / API keys
- Horizontal scaling with Redis-backed rate limiter and distributed locks
- Leaderboard time-window filters (weekly / monthly)
