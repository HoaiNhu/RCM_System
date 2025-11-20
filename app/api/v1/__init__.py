"""API v1 routes"""
from fastapi import APIRouter
from .health import router as health_router
from .recommendations import router as recommendations_router
from .model import router as model_router
from .debug import router as debug_router


# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(health_router)
api_router.include_router(recommendations_router)
api_router.include_router(model_router)
api_router.include_router(debug_router)

__all__ = ["api_router"]
