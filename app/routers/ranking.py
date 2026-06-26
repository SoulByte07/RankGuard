from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import RankingListResponse
from app.services.ranking import compute_rankings, get_rankings

router = APIRouter()


@router.get("/ranking", response_model=RankingListResponse)
async def get_rankings_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    entries, total = await get_rankings(db, limit=limit, offset=offset)
    return RankingListResponse(count=total, results=entries)


@router.post("/ranking/compute")
async def compute_rankings_endpoint(
    db: AsyncSession = Depends(get_db),
):
    await compute_rankings(db)
    return {"status": "ok"}
