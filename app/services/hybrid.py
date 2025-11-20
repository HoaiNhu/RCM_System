"""
Hybrid Recommendation Strategy combining Collaborative Filtering and Content-Based Filtering
"""
import numpy as np
from typing import List, Optional, Dict, Any

from .base import IRecommendationStrategy, IModelTrainer
from .collaborative_filtering import CollaborativeFilteringStrategy
from .content_based import ContentBasedFilteringStrategy
from ..repositories import ProductRepository
from ..core.config import Settings


class HybridRecommendationStrategy(IRecommendationStrategy, IModelTrainer):
    """
    Hybrid strategy combining CF and Content-Based recommendations
    Uses weighted scoring to balance both approaches
    Follows Dependency Inversion Principle - depends on abstractions (IRecommendationStrategy)
    """
    
    def __init__(
        self,
        cf_strategy: CollaborativeFilteringStrategy,
        content_strategy: ContentBasedFilteringStrategy,
        product_repo: ProductRepository,
        settings: Settings,
        cf_weight: float = 0.7,
        content_weight: float = 0.3
    ):
        self.cf_strategy = cf_strategy
        self.content_strategy = content_strategy
        self.product_repo = product_repo
        self.settings = settings
        self.cf_weight = cf_weight
        self.content_weight = content_weight
    
    def recommend(self, user_id: str, n_items: int = 5, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate hybrid recommendations by combining CF and Content-Based scores
        """
        try:
            # Get candidates from both strategies
            cf_recommendations = []
            content_recommendations = []
            
            # Try collaborative filtering first
            if self.cf_strategy.is_ready():
                cf_recommendations = self.cf_strategy.recommend(
                    user_id, 
                    n_items=n_items * 3,  # Get more candidates for scoring
                    context=context
                )
            
            # Try content-based filtering
            if self.content_strategy.is_ready():
                content_recommendations = self.content_strategy.recommend(
                    user_id,
                    n_items=n_items * 3,
                    context=context
                )
            
            # If neither strategy is ready, use fallback
            if not cf_recommendations and not content_recommendations:
                return self._fallback_recommendations(user_id, n_items, context)
            
            # Combine candidate products
            all_candidates = list(set(cf_recommendations + content_recommendations))
            
            # If we have candidates, score them with hybrid approach
            if all_candidates:
                scored_products = self._score_candidates(user_id, all_candidates, context)
                
                # Sort by hybrid score and take top N
                sorted_products = sorted(scored_products.items(), key=lambda x: x[1], reverse=True)
                recommendations = [pid for pid, _ in sorted_products[:n_items]]
                
                return recommendations
            
            # Fallback if no candidates
            return self._fallback_recommendations(user_id, n_items, context)
            
        except Exception as e:
            print(f"Error in hybrid recommend: {e}")
            return self._fallback_recommendations(user_id, n_items, context)
    
    def _score_candidates(self, user_id: str, product_ids: List[str], context: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """
        Score candidate products using weighted combination of CF and Content-Based scores
        """
        try:
            # Get scores from both strategies
            cf_scores = {}
            content_scores = {}
            
            if self.cf_strategy.is_ready():
                cf_scores = self.cf_strategy.get_scores(user_id, product_ids, context)
            
            if self.content_strategy.is_ready():
                content_scores = self.content_strategy.get_scores(user_id, product_ids, context)
            
            # Normalize scores to 0-1 range
            cf_scores = self._normalize_scores(cf_scores)
            content_scores = self._normalize_scores(content_scores)
            
            # Compute hybrid scores
            hybrid_scores = {}
            for product_id in product_ids:
                cf_score = cf_scores.get(product_id, 0.0)
                content_score = content_scores.get(product_id, 0.0)
                
                # Weighted combination
                hybrid_score = (
                    self.cf_weight * cf_score +
                    self.content_weight * content_score
                )
                
                # Boost score if product appears in both strategies
                if cf_score > 0 and content_score > 0:
                    hybrid_score *= 1.2  # 20% boost for consensus
                
                hybrid_scores[product_id] = hybrid_score
            
            return hybrid_scores
            
        except Exception as e:
            print(f"Error scoring candidates: {e}")
            return {pid: 0.0 for pid in product_ids}
    
    def _normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Normalize scores to 0-1 range"""
        if not scores:
            return {}
        
        values = list(scores.values())
        min_val = min(values)
        max_val = max(values)
        
        if max_val == min_val:
            return {k: 1.0 if v > 0 else 0.0 for k, v in scores.items()}
        
        return {
            k: (v - min_val) / (max_val - min_val)
            for k, v in scores.items()
        }
    
    def get_scores(self, user_id: str, product_ids: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Get hybrid scores for specific products"""
        return self._score_candidates(user_id, product_ids, context)
    
    def _fallback_recommendations(self, user_id: str, n_items: int, context: Optional[Dict[str, Any]]) -> List[str]:
        """Fallback to popular products when strategies fail"""
        try:
            current_product_id = context.get('current_product_id') if context else None
            
            # If there's a current product, try similar by category
            if current_product_id:
                product = self.product_repo.find_by_id(current_product_id)
                if product and 'productCategory' in product:
                    category_products = self.product_repo.get_by_category(
                        str(product['productCategory']),
                        limit=n_items + 5
                    )
                    recommendations = [
                        str(p['_id']) for p in category_products
                        if str(p['_id']) != current_product_id
                    ][:n_items]
                    
                    if recommendations:
                        return recommendations
            
            # Fallback to popular products
            popular = self.product_repo.get_popular_products(
                limit=n_items,
                min_rating=self.settings.MIN_RATING_THRESHOLD
            )
            return [str(p['_id']) for p in popular]
            
        except Exception as e:
            print(f"Error in fallback recommendations: {e}")
            return []
    
    def train(self, force_retrain: bool = False) -> bool:
        """Train the collaborative filtering model (content-based doesn't need training)"""
        try:
            print("\n" + "="*60)
            print("🔨 TRAINING HYBRID RECOMMENDATION SYSTEM")
            print("="*60)
            
            # Train CF model
            print("\n[1/2] Training Collaborative Filtering model...")
            cf_success = self.cf_strategy.train(force_retrain)
            if cf_success:
                print("      ✅ Collaborative Filtering trained successfully")
            else:
                print("      ⚠️  Collaborative Filtering training failed")
            
            # Content-based is already built in __init__
            print("\n[2/2] Checking Content-Based model...")
            content_ready = self.content_strategy.is_ready()
            if content_ready:
                print("      ✅ Content-Based model ready")
            else:
                print("      ⚠️  Content-Based model not ready")
            
            if cf_success and content_ready:
                print("✓ Hybrid system ready: CF and Content-Based")
                return True
            elif cf_success:
                print("⚠ Hybrid system partial: CF only")
                return True
            elif content_ready:
                print("⚠ Hybrid system partial: Content-Based only")
                return True
            else:
                print("✗ Hybrid system training failed")
                return False
                
        except Exception as e:
            print(f"Error training hybrid system: {e}")
            return False
    
    def evaluate(self) -> Dict[str, float]:
        """Evaluate using CF metrics (primary model)"""
        return self.cf_strategy.evaluate()
    
    def is_ready(self) -> bool:
        """Check if at least one strategy is ready"""
        return self.cf_strategy.is_ready() or self.content_strategy.is_ready()
    
    def get_strategy_status(self) -> Dict[str, bool]:
        """Get status of both strategies"""
        return {
            'collaborative_filtering': self.cf_strategy.is_ready(),
            'content_based': self.content_strategy.is_ready(),
            'hybrid': self.is_ready()
        }
