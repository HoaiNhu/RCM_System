"""Model management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict

from ...core.dependencies import get_recommendation_service
from ...schemas import ModelEvaluationResponse
from ...services import HybridRecommendationStrategy


router = APIRouter(prefix="/model", tags=["Model Management"])


@router.get("/evaluate", response_model=ModelEvaluationResponse)
async def evaluate_model(
    service: HybridRecommendationStrategy = Depends(get_recommendation_service)
):
    """
    Evaluate model performance using precision, recall, and F1 score
    """
    try:
        if not service.is_ready():
            raise HTTPException(status_code=503, detail="Model not ready for evaluation")
        
        metrics = service.evaluate()
        
        return ModelEvaluationResponse(
            precision=metrics['precision'],
            recall=metrics['recall'],
            f1_score=metrics['f1'],
            message=f"Evaluation complete. F1: {metrics['f1']:.4f}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating model: {str(e)}")


@router.post("/update", response_model=Dict)
async def update_model(
    background_tasks: BackgroundTasks,
    service: HybridRecommendationStrategy = Depends(get_recommendation_service)
):
    """
    Trigger model update/retraining in the background
    """
    try:
        # Schedule training in background
        background_tasks.add_task(service.train, force_retrain=True)
        
        return {
            "message": "Model update scheduled",
            "status": "training_started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scheduling model update: {str(e)}")


@router.post("/train", response_model=Dict)
async def train_model_sync(
    service: HybridRecommendationStrategy = Depends(get_recommendation_service)
):
    """
    Train model synchronously (blocking operation - use with caution)
    """
    try:
        success = service.train(force_retrain=True)
        
        if success:
            return {
                "message": "Model trained successfully",
                "status": "ready"
            }
        else:
            raise HTTPException(status_code=500, detail="Model training failed")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error training model: {str(e)}")
