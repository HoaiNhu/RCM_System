"""Services layer for business logic"""
from .base import IRecommendationStrategy, IModelTrainer, IDataProcessor
from .collaborative_filtering import CollaborativeFilteringStrategy
from .content_based import ContentBasedFilteringStrategy
from .hybrid import HybridRecommendationStrategy
from .additional_services import QuizRecommendationService, PopularProductService

__all__ = [
    "IRecommendationStrategy",
    "IModelTrainer",
    "IDataProcessor",
    "CollaborativeFilteringStrategy",
    "ContentBasedFilteringStrategy",
    "HybridRecommendationStrategy",
    "QuizRecommendationService",
    "PopularProductService",
]
