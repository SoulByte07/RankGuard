from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ranking, UserSnapshot
from app.schemas import SummaryResponse


async def get_user_summary(db: AsyncSession, user_id: UUID) -> SummaryResponse | None:
    result = await db.execute(
        select(UserSnapshot).where(UserSnapshot.user_id == user_id)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        return None

    result = await db.execute(
        select(Ranking.rank).where(Ranking.user_id == user_id)
    )
    rank = result.scalar_one_or_none()

    return SummaryResponse(
        user_id=snapshot.user_id,
        total_earned=snapshot.total_earned,
        total_spent=snapshot.total_spent,
        net_balance=snapshot.net_balance,
        transaction_count=snapshot.transaction_count,
        bonus_count=snapshot.bonus_count,
        rank=rank,
        last_activity=snapshot.last_activity,
    )
