"""Health check and system status routes"""
from fastapi import APIRouter, Depends
from typing import Dict

from ...core.dependencies import get_db, get_redis, get_recommendation_service
from ...schemas import HealthResponse, ModelStatusResponse
from ...services import HybridRecommendationStrategy


router = APIRouter(tags=["Health & Status"])


@router.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "RCM System API - Hybrid Recommendation Engine",
        "status": "running",
        "version": "2.0.0"
    }


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db=Depends(get_db),
    redis_client=Depends(get_redis),
    service: HybridRecommendationStrategy = Depends(get_recommendation_service)
):
    """
    Comprehensive health check endpoint
    Returns status of database, Redis, and recommendation models
    """
    try:
        # Check database
        db_status = "connected" if db is not None else "disconnected"
        
        # Check Redis
        redis_status = "connected" if redis_client is not None else "disconnected"
        
        # Check model status
        model_status = "ready" if service.is_ready() else "not_ready"
        
        # Get detailed strategy status
        strategy_status = service.get_strategy_status()
        
        overall_status = "healthy" if all([
            db_status == "connected",
            model_status == "ready"
        ]) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            database=db_status,
            redis=redis_status,
            model=f"{model_status} (CF: {strategy_status['collaborative_filtering']}, CB: {strategy_status['content_based']})"
        )
        
    except Exception as e:
        return HealthResponse(
            status="error",
            database="unknown",
            redis="unknown",
            model=f"error: {str(e)}"
        )


@router.get("/status", response_model=ModelStatusResponse)
async def model_status(
    service: HybridRecommendationStrategy = Depends(get_recommendation_service)
):
    """Get detailed model status"""
    try:
        strategy_status = service.get_strategy_status()
        
        # Get CF model details
        n_users = None
        n_products = None
        last_updated = None
        
        if service.cf_strategy.is_ready():
            n_users = len(service.cf_strategy.user_to_idx)
            n_products = len(service.cf_strategy.product_to_idx)
        
        status = "ready" if service.is_ready() else "not_ready"
        
        return ModelStatusResponse(
            status=status,
            n_users=n_users,
            n_products=n_products,
            last_updated=last_updated,
            error=None if service.is_ready() else "Model not initialized"
        )
        
    except Exception as e:
        return ModelStatusResponse(
            status="error",
            n_users=None,
            n_products=None,
            last_updated=None,
            error=str(e)
        )
