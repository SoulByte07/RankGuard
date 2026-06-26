from fastapi import FastAPI

from app.database import engine
from app.routers.summary import router as summary_router
from app.routers.transaction import router as transaction_router

app = FastAPI(title="RankGuard")
app.include_router(transaction_router)
app.include_router(summary_router)


@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()


@app.get("/health")
async def health():
    return {"status": "ok"}
