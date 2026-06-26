from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID 


async def get_user_summary(db: AsyncSession, user_id: UUID) -> SummaryResponse | None:
    """
    Fetch user summary from the database.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.

    Returns:
        SummaryResponse | None: The user summary or None if not found.
    """
    # Query to fetch user snapshot and join with rankings
    result = await db.execute(
        select(UserSnapshot, Ranking)
        .join(Ranking, UserSnapshot.rank_id == Ranking.id)
        .where(UserSnapshot.user_id == user_id)
    )
    
    user_summary = result.first()
    
    if not user_summary:
        return None  # User not found, return None for 404 handling
    
    # Construct and return the SummaryResponse
    return SummaryResponse(
        user_id=user_summary.UserSnapshot.user_id,
        rank=user_summary.Ranking.rank_name,
        score=user_summary.UserSnapshot.score,
        last_updated=user_summary.UserSnapshot.last_updated
    )

