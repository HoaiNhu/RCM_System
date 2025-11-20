"""
Dependency injection following Dependency Inversion Principle
"""
import pymongo
import redis
from typing import Optional
from functools import lru_cache

from .config import get_settings
from ..repositories import (
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
from ..services import (
    CollaborativeFilteringStrategy,
    ContentBasedFilteringStrategy,
    HybridRecommendationStrategy,
    QuizRecommendationService,
    PopularProductService,
)


# Global instances (lazy initialization)
_db = None
_redis_client = None
_hybrid_service = None


def get_db():
    """Get MongoDB database connection (Singleton)"""
    global _db
    if _db is None:
        settings = get_settings()
        try:
            client = pymongo.MongoClient(settings.mongodb_uri)
            _db = client[settings.MONGODB_DATABASE]
            _db.command("ping")
            print(f"✓ MongoDB connected: {settings.MONGODB_DATABASE}")
        except Exception as e:
            print(f"✗ MongoDB connection failed: {e}")
            _db = None
    return _db


def get_redis() -> Optional[redis.Redis]:
    """Get Redis connection (Singleton)"""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        try:
            _redis_client = redis.Redis(
                host=settings.UPSTASH_REDIS_HOST,
                port=settings.UPSTASH_REDIS_PORT,
                password=settings.UPSTASH_REDIS_PASSWORD,
                ssl=True,
                decode_responses=True
            )
            _redis_client.ping()
            print("✓ Redis connected")
        except Exception as e:
            print(f"⚠ Redis connection failed: {e}")
            _redis_client = None
    return _redis_client


def get_recommendation_service() -> HybridRecommendationStrategy:
    """Get hybrid recommendation service (Singleton with lazy loading)"""
    global _hybrid_service
    
    if _hybrid_service is None:
        settings = get_settings()
        db = get_db()
        
        if db is None:
            raise Exception("Database connection required")
        
        # Initialize repositories
        order_repo = OrderRepository(db)
        rating_repo = RatingRepository(db)
        product_repo = ProductRepository(db)
        search_repo = SearchHistoryRepository(db)
        metadata_repo = ModelMetadataRepository(db)
        
        # Initialize strategies
        cf_strategy = CollaborativeFilteringStrategy(
            order_repo=order_repo,
            rating_repo=rating_repo,
            product_repo=product_repo,
            search_repo=search_repo,
            metadata_repo=metadata_repo,
            settings=settings
        )
        
        content_strategy = ContentBasedFilteringStrategy(
            product_repo=product_repo,
            search_repo=search_repo,
            settings=settings
        )
        
        # Initialize hybrid service
        _hybrid_service = HybridRecommendationStrategy(
            cf_strategy=cf_strategy,
            content_strategy=content_strategy,
            product_repo=product_repo,
            settings=settings,
            cf_weight=0.3,  # Reduced - synthetic data quality issue
            content_weight=0.7  # Increased - more reliable
        )
        
        # Show strategy status
        status = _hybrid_service.get_strategy_status()
        print("\n✓ Hybrid recommendation service initialized")
        print(f"   • Collaborative Filtering: {'✅ Ready' if status['collaborative_filtering'] else '⚠️  Not Ready (will use Content-Based + Fallback)'}")
        print(f"   • Content-Based: {'✅ Ready' if status['content_based'] else '❌ Not Ready'}")
        print(f"   • Hybrid System: {'✅ Ready' if status['hybrid'] else '❌ Not Ready'}")
    
    return _hybrid_service


def get_quiz_service() -> QuizRecommendationService:
    """Get quiz recommendation service"""
    settings = get_settings()
    db = get_db()
    
    if db is None:
        raise Exception("Database connection required")
    
    return QuizRecommendationService(
        product_repo=ProductRepository(db),
        quiz_response_repo=QuizResponseRepository(db),
        quiz_repo=QuizRepository(db),
        settings=settings
    )


def get_popular_service() -> PopularProductService:
    """Get popular product service"""
    settings = get_settings()
    db = get_db()
    
    if db is None:
        raise Exception("Database connection required")
    
    return PopularProductService(
        product_repo=ProductRepository(db),
        settings=settings
    )
