from fastapi import APIRouter
from .hardware import router as hardware_router
from .crawler import router as crawler_router
from .validator import router as validator_router
from .deals import router as deals_router
from .alerts import router as alerts_router
from .health import router as health_router
from .config import router as config_router

api_router = APIRouter(prefix="/api")
api_router.include_router(hardware_router)
api_router.include_router(crawler_router)
api_router.include_router(validator_router)
api_router.include_router(deals_router)
api_router.include_router(alerts_router)
api_router.include_router(health_router)
api_router.include_router(config_router)
