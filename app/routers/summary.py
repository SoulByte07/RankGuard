from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SummaryResponse
from app.services.summary import get_user_summary

router = APIRouter()


@router.get("/summary/{user_id}", response_model=SummaryResponse)
async def get_summary_endpoint(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    summary = await get_user_summary(db, user_id)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return summary
