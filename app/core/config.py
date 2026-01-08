"""
Core configuration module following Single Responsibility Principle
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variables"""
    
    # MongoDB Settings
    MONGODB_USERNAME: str
    MONGODB_PASSWORD: str
    MONGODB_DATABASE: str = "test"
    MONGODB_CLUSTER: str = "webbuycake.asd8v.mongodb.net"
    
    # Redis Settings
    UPSTASH_REDIS_HOST: str
    UPSTASH_REDIS_PORT: int = 6379
    UPSTASH_REDIS_PASSWORD: str
    
    # Model Settings
    MODEL_PATH: str = "model.pkl"
    MAPPINGS_PATH: str = "mappings.pkl"
    N_COMPONENTS: int = 15  # Increased from 10 for better feature learning
    MAX_ITER: int = 100  # Increased from 50 for better convergence
    
    # Cache Settings
    CACHE_TTL: int = 3600  # 1 hour
    
    # Recommendation Settings
    DEFAULT_N_ITEMS: int = 5
    MIN_RATING_THRESHOLD: float = 2.5  # Lowered for better recall
    SCORE_THRESHOLD: float = 0.1  # Lowered significantly for diversity
    MIN_TOTAL_RATINGS: int = 1  # Lowered to include more products
    
    @property
    def mongodb_uri(self) -> str:
        """Generate MongoDB connection URI"""
        return (
            f"mongodb+srv://{self.MONGODB_USERNAME}:{self.MONGODB_PASSWORD}"
            f"@{self.MONGODB_CLUSTER}/?retryWrites=true&w=majority&appName=WebBuyCake"
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (Singleton pattern)"""
    return Settings()
