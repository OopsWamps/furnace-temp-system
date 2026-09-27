from fastapi import APIRouter
from app.api import health, furnace

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router)
api_router.include_router(furnace.router)

__all__ = ["api_router"]
