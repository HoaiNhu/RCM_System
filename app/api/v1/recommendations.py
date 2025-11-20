"""Recommendation endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict

from ...core.dependencies import (
    get_recommendation_service,
    get_quiz_service,
    get_popular_service,
    get_redis
)
from ...schemas import (
    RecommendationRequest,
    PopularRequest,
    QuizRecommendationRequest,
    RecommendationResponse
)
from ...services import (
    HybridRecommendationStrategy,
    QuizRecommendationService,
    PopularProductService
)
import json


router = APIRouter(prefix="/recommend", tags=["Recommendations"])


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    service: HybridRecommendationStrategy = Depends(get_recommendation_service),
    redis_client = Depends(get_redis)
):
    """
    Get personalized recommendations for a user using Hybrid approach (CF + Content-Based)
    
    - **user_id**: User ID to get recommendations for
    - **product_id**: Optional current product ID for context-aware recommendations
    - **n_items**: Number of items to recommend (default: 5)
    """
    try:
        # Check cache first
        cache_key = f"hybrid_rec:{request.user_id}:{request.product_id or 'none'}:{request.n_items}"
        
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                return RecommendationResponse(
                    recommendations=json.loads(cached),
                    source="cache",
                    user_id=request.user_id
                )
        
        # Get recommendations from hybrid service
        context = {'current_product_id': request.product_id} if request.product_id else None
        
        recommendations = service.recommend(
            user_id=request.user_id,
            n_items=request.n_items,
            context=context
        )
        
        if not recommendations:
            raise HTTPException(status_code=404, detail="No recommendations found for this user")
        
        # Cache result
        if redis_client:
            redis_client.setex(cache_key, 3600, json.dumps(recommendations))
        
        # Determine source
        source = "hybrid"
        if service.cf_strategy.is_ready() and service.content_strategy.is_ready():
            source = "hybrid (CF + Content-Based)"
        elif service.cf_strategy.is_ready():
            source = "collaborative_filtering"
        elif service.content_strategy.is_ready():
            source = "content_based"
        else:
            source = "fallback"
        
        return RecommendationResponse(
            recommendations=recommendations,
            source=source,
            user_id=request.user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.post("/popular", response_model=Dict)
async def get_popular_products(
    request: PopularRequest,
    service: PopularProductService = Depends(get_popular_service)
):
    """
    Get popular products, optionally filtered by category
    
    - **category**: Optional category ID to filter products
    - **n_items**: Number of items to return (default: 5)
    """
    try:
        n_items = request.n_items if request.n_items else 5
        
        recommendations = service.get_popular_products(
            category_id=request.category,
            n_items=n_items
        )
        
        # If no recommendations found, try without category filter
        if not recommendations and request.category:
            print(f"⚠️  No products found in category {request.category}, trying all products...")
            recommendations = service.get_popular_products(
                category_id=None,
                n_items=n_items
            )
        
        if not recommendations:
            raise HTTPException(
                status_code=404, 
                detail="No products found. Please add products to the database."
            )
        
        return {
            "recommendations": recommendations,
            "source": "popular" if not request.category else f"popular (category: {request.category})",
            "category": request.category
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting popular products: {str(e)}")


@router.post("/quiz", response_model=Dict)
async def get_quiz_recommendations(
    request: QuizRecommendationRequest,
    service: QuizRecommendationService = Depends(get_quiz_service),
    popular_service: PopularProductService = Depends(get_popular_service),
    redis_client = Depends(get_redis)
):
    """
    Get recommendations based on quiz responses
    
    - **user_id**: User ID
    - **session_id**: Quiz session ID
    - **n_items**: Number of items to recommend (default: 20)
    """
    try:
        # Check cache
        cache_key = f"quiz_rec:{request.user_id}:{request.session_id}"
        
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                return {
                    "recommendations": json.loads(cached),
                    "source": "cache",
                    "user_id": request.user_id,
                    "session_id": request.session_id
                }
        
        n_items = request.n_items if request.n_items else 20
        
        recommendations = service.recommend_from_quiz(
            user_id=request.user_id,
            session_id=request.session_id,
            n_items=n_items
        )
        
        source = "quiz"
        
        # Fallback to popular products if no quiz data
        if not recommendations:
            print(f"⚠️  No quiz data for session {request.session_id}, using popular products...")
            recommendations = popular_service.get_popular_products(n_items=n_items)
            source = "popular (no quiz data)"
        
        if not recommendations:
            raise HTTPException(
                status_code=404, 
                detail="No recommendations found. Please add products to the database."
            )
        
        # Cache result
        if redis_client:
            redis_client.setex(cache_key, 3600, json.dumps(recommendations))
        
        return {
            "recommendations": recommendations,
            "source": source,
            "user_id": request.user_id,
            "session_id": request.session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting quiz recommendations: {str(e)}")
