"""Debug and testing endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict

from ...core.dependencies import get_db, get_redis
from ...schemas import InteractionLogRequest


router = APIRouter(prefix="/debug", tags=["Debug & Testing"])


@router.get("/connection", response_model=Dict)
async def test_connections(
    db = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Test database and Redis connections"""
    try:
        db_status = "connected" if db is not None else "disconnected"
        redis_status = "connected" if redis_client is not None else "disconnected"
        
        # Test database query
        db_test = None
        if db:
            try:
                db.command("ping")
                db_test = "ping successful"
            except Exception as e:
                db_test = f"ping failed: {str(e)}"
        
        # Test Redis query
        redis_test = None
        if redis_client:
            try:
                redis_client.ping()
                redis_test = "ping successful"
            except Exception as e:
                redis_test = f"ping failed: {str(e)}"
        
        return {
            "database": {
                "status": db_status,
                "test": db_test
            },
            "redis": {
                "status": redis_status,
                "test": redis_test
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing connections: {str(e)}")


@router.get("/data", response_model=Dict)
async def get_data_stats(
    db = Depends(get_db)
):
    """Get statistics about data in database"""
    try:
        if db is None:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        stats = {
            "users": db.users.count_documents({}),
            "products": db.products.count_documents({}),
            "orders": db.orders.count_documents({}),
            "ratings": db.ratings.count_documents({}),
            "searchHistory": db.searchHistory.count_documents({})
        }
        
        return {
            "collection_counts": stats,
            "total_documents": sum(stats.values())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting data stats: {str(e)}")


@router.post("/interaction/log", response_model=Dict)
async def log_interaction(
    request: InteractionLogRequest,
    db = Depends(get_db)
):
    """Log user interaction for future model improvements"""
    try:
        if db is None:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        from datetime import datetime
        
        interaction = {
            "userId": request.user_id,
            "productId": request.product_id,
            "interactionType": request.interaction_type,
            "metadata": request.metadata or {},
            "createdAt": datetime.utcnow()
        }
        
        result = db.interactions.insert_one(interaction)
        
        return {
            "message": "Interaction logged successfully",
            "interaction_id": str(result.inserted_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging interaction: {str(e)}")
