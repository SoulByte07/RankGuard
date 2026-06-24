from fastapi import FastAPI

from app.database import engine

app = FastAPI(title="RankGuard")


@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()


@app.get("/health")
async def health():
    return {"status": "ok"}
