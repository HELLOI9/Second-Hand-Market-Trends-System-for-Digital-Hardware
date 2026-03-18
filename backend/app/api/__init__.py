from fastapi import APIRouter
from .hardware import router as hardware_router
from .crawler import router as crawler_router

api_router = APIRouter(prefix="/api")
api_router.include_router(hardware_router)
api_router.include_router(crawler_router)
