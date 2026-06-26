from fastapi import FastAPI

from app.config import settings
from app.database import engine
from app.middlewares.rate_limit import RateLimitMiddleware
from app.routers.ranking import router as ranking_router
from app.routers.summary import router as summary_router
from app.routers.transaction import router as transaction_router

app = FastAPI(title="RankGuard")
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
app.include_router(transaction_router)
app.include_router(summary_router)
app.include_router(ranking_router)


@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()


@app.get("/health")
async def health():
    return {"status": "ok"}
