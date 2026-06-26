from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ranking, UserSnapshot
from app.schemas import RankingEntry


async def compute_rankings(db: AsyncSession) -> None:
    result = await db.execute(select(UserSnapshot))
    snapshots = result.scalars().all()

    now = datetime.now(timezone.utc)
    entries: list[tuple[object, Decimal, datetime]] = []
    for s in snapshots:
        days_since = (now - s.last_activity).days
        score = (
            s.total_earned * Decimal("1.0")
            + s.total_spent * Decimal("0.5")
            + Decimal(s.transaction_count) * Decimal("10")
            + Decimal(s.bonus_count) * Decimal("50")
            - Decimal(days_since) * Decimal("0.1")
        )
        entries.append((s.user_id, score, s.last_activity))

    entries.sort(key=lambda x: (-x[1], x[2]))

    await db.execute(delete(Ranking))
    db.add_all(
        [
            Ranking(user_id=uid, score=score, rank=i)
            for i, (uid, score, _) in enumerate(entries, start=1)
        ]
    )
    await db.commit()


async def get_rankings(
    db: AsyncSession, limit: int = 50, offset: int = 0
) -> tuple[list[RankingEntry], int]:
    count_result = await db.execute(select(sa_func.count()).select_from(Ranking))
    total = count_result.scalar() or 0

    if total == 0:
        await compute_rankings(db)
        count_result = await db.execute(select(sa_func.count()).select_from(Ranking))
        total = count_result.scalar() or 0
        if total == 0:
            return [], 0

    result = await db.execute(
        select(Ranking, UserSnapshot)
        .join(UserSnapshot, Ranking.user_id == UserSnapshot.user_id)
        .order_by(Ranking.rank)
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()

    entries = [
        RankingEntry(
            rank=ranking.rank,
            user_id=ranking.user_id,
            score=ranking.score,
            total_earned=snapshot.total_earned,
            total_spent=snapshot.total_spent,
            transaction_count=snapshot.transaction_count,
        )
        for ranking, snapshot in rows
    ]

    return entries, total
