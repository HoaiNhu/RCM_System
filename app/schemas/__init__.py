"""
Request and Response schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class RecommendationRequest(BaseModel):
    """Request schema for user recommendations"""
    user_id: str = Field(..., description="User ID to get recommendations for")
    product_id: Optional[str] = Field(None, description="Current product ID for context-aware recommendations")
    n_items: Optional[int] = Field(5, ge=1, le=50, description="Number of items to recommend")


class PopularRequest(BaseModel):
    """Request schema for popular products"""
    category: Optional[str] = Field(None, description="Category ID to filter products")
    n_items: Optional[int] = Field(5, ge=1, le=50, description="Number of items to return")


class QuizRecommendationRequest(BaseModel):
    """Request schema for quiz-based recommendations"""
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Quiz session ID")
    n_items: Optional[int] = Field(20, ge=1, le=50, description="Number of items to recommend")


class InteractionLogRequest(BaseModel):
    """Request schema for logging user interactions"""
    user_id: str = Field(..., description="User ID")
    product_id: str = Field(..., description="Product ID")
    interaction_type: str = Field(..., description="Type of interaction: view, click, search, etc.")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class RecommendationResponse(BaseModel):
    """Response schema for recommendations"""
    recommendations: List[str] = Field(..., description="List of recommended product IDs")
    source: str = Field(..., description="Source of recommendations: model, fallback, cache, etc.")
    user_id: str = Field(..., description="User ID for which recommendations were generated")


class ModelStatusResponse(BaseModel):
    """Response schema for model status"""
    status: str = Field(..., description="Model status: ready, training, error")
    n_users: Optional[int] = Field(None, description="Number of users in model")
    n_products: Optional[int] = Field(None, description="Number of products in model")
    last_updated: Optional[str] = Field(None, description="Last model update timestamp")
    error: Optional[str] = Field(None, description="Error message if any")


class ModelEvaluationResponse(BaseModel):
    """Response schema for model evaluation metrics"""
    precision: float = Field(..., description="Average precision score")
    recall: float = Field(..., description="Average recall score")
    f1_score: float = Field(..., description="F1 score")
    message: str = Field(..., description="Evaluation message")


class HealthResponse(BaseModel):
    """Response schema for health check"""
    status: str = Field(..., description="Overall health status")
    database: str = Field(..., description="Database connection status")
    redis: str = Field(..., description="Redis connection status")
    model: str = Field(..., description="Model status")
