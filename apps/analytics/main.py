"""
main.py — FastAPI analytics service entrypoint.

Usage:
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload
    python main.py
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.events import router as events_router
from api.health import router as health_router
from api.predict import router as predict_router
from api.recommend import router as recommend_router
from api.persona import router as persona_router
from features.pipeline import run_feature_pipeline_loop
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(
        run_feature_pipeline_loop(settings.feature_pipeline_interval_minutes)
    )
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="theNewslane Predictive Analytics",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(events_router, prefix="/api/v1")
app.include_router(predict_router, prefix="/api/v1")
app.include_router(recommend_router, prefix="/api/v1")
app.include_router(persona_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
