"""
Abstract base classes for recommendation strategies following Strategy Pattern and Open/Closed Principle
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import numpy as np


class IRecommendationStrategy(ABC):
    """Interface for recommendation strategies"""
    
    @abstractmethod
    def recommend(self, user_id: str, n_items: int = 5, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Generate recommendations for a user"""
        pass
    
    @abstractmethod
    def get_scores(self, user_id: str, product_ids: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Get recommendation scores for specific products"""
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """Check if strategy is ready to use"""
        pass


class IModelTrainer(ABC):
    """Interface for model training"""
    
    @abstractmethod
    def train(self, force_retrain: bool = False) -> bool:
        """Train or update the model"""
        pass
    
    @abstractmethod
    def evaluate(self) -> Dict[str, float]:
        """Evaluate model performance"""
        pass


class IDataProcessor(ABC):
    """Interface for data processing"""
    
    @abstractmethod
    def prepare_interaction_matrix(self, after_timestamp: Optional[Any] = None) -> Optional[np.ndarray]:
        """Prepare user-item interaction matrix"""
        pass
    
    @abstractmethod
    def prepare_content_features(self) -> Optional[np.ndarray]:
        """Prepare content features for products"""
        pass
