"""Repository layer for data access"""
from .base import IRepository, BaseRepository
from .repositories import (
    UserRepository,
    ProductRepository,
    OrderRepository,
    RatingRepository,
    SearchHistoryRepository,
    QuizResponseRepository,
    QuizRepository,
    ModelMetadataRepository,
    RecommendationRepository,
)

__all__ = [
    "IRepository",
    "BaseRepository",
    "UserRepository",
    "ProductRepository",
    "OrderRepository",
    "RatingRepository",
    "SearchHistoryRepository",
    "QuizResponseRepository",
    "QuizRepository",
    "ModelMetadataRepository",
    "RecommendationRepository",
]
