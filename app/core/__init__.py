"""Core module for configuration and dependencies"""
from .config import Settings, get_settings
from .dependencies import (
    get_db,
    get_redis,
    get_recommendation_service,
)

__all__ = [
    "Settings",
    "get_settings",
    "get_db",
    "get_redis",
    "get_recommendation_service",
]
