from fastapi import APIRouter

router = APIRouter()

"""
- `GET /ranking?limit=50&offset=0` → returns `RankingListResponse`
- Trigger `compute_rankings` if results are stale (or run in background task)
"""


@router.get("/ranking")
async def get_rankings():
    return {"message": "rankings"}


@router.post("/ranking")
async def compute_rankings():
    return {"message": "rankings computed"}
