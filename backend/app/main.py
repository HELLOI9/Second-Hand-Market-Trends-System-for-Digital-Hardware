import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.scheduler.jobs import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(
    title="闲鱼数码硬件行情系统",
    version="0.1.0",
    description="Second-Hand Digital Hardware Market Trends",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def startup():
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()


@app.get("/health")
async def health():
    return {"status": "ok"}
