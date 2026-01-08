"""
Hybrid Recommendation Strategy combining Collaborative Filtering and Content-Based Filtering
"""
import numpy as np
from typing import List, Optional, Dict, Any

from .base import IRecommendationStrategy, IModelTrainer
from .collaborative_filtering import CollaborativeFilteringStrategy
from .content_based import ContentBasedFilteringStrategy
from .simple_rules import SimpleRuleBasedRecommendation
from ..repositories import ProductRepository, OrderRepository, RatingRepository
from ..core.config import Settings


class HybridRecommendationStrategy(IRecommendationStrategy, IModelTrainer):
    """
    Hybrid strategy combining CF, Content-Based, and Simple Rules
    Uses weighted scoring to balance both approaches
    Falls back to Simple Rules when CF fails
    """
    
    def __init__(
        self,
        cf_strategy: CollaborativeFilteringStrategy,
        content_strategy: ContentBasedFilteringStrategy,
        product_repo: ProductRepository,
        settings: Settings,
        order_repo: Optional[OrderRepository] = None,
        rating_repo: Optional[RatingRepository] = None,
        cf_weight: float = 0.7,
        content_weight: float = 0.3
    ):
        self.cf_strategy = cf_strategy
        self.content_strategy = content_strategy
        self.product_repo = product_repo
        self.settings = settings
        self.cf_weight = cf_weight
        self.content_weight = content_weight
        
        # Initialize Simple Rules as fallback
        self.simple_rules = SimpleRuleBasedRecommendation(
            product_repo=product_repo,
            order_repo=order_repo or getattr(product_repo, 'order_repo', None),
            rating_repo=rating_repo or getattr(product_repo, 'rating_repo', None)
        )
    
    def recommend(self, user_id: str, n_items: int = 5, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate hybrid recommendations - CF + Content-Based OR Simple Rules if CF fails
        """
        try:
            # Get candidates from both strategies (balanced for precision-recall)
            cf_recommendations = []
            content_recommendations = []
            
            # Try collaborative filtering first
            if self.cf_strategy.is_ready():
                cf_recommendations = self.cf_strategy.recommend(
                    user_id, 
                    n_items=int(n_items * 2.5),  # Increased from 2 to 2.5 for better recall
                    context=context
                )
                print(f"📊 CF returned: {len(cf_recommendations)} candidates")
            
            # CRITICAL: If CF returns nothing, use Simple Rules immediately
            if len(cf_recommendations) == 0:
                print(f"⚠️  CF returned 0 candidates, switching to Simple Rules")
                return self._simple_rules_recommendation(user_id, n_items, context)
            
            # Try content-based filtering
            if self.content_strategy.is_ready():
                content_recommendations = self.content_strategy.recommend(
                    user_id,
                    n_items=int(n_items * 2.5),  # Increased from 2 to 2.5
                    context=context
                )
                print(f"🎨 Content returned: {len(content_recommendations)} candidates")
            
            # If BOTH strategies return nothing or very few, use simple rules
            total_candidates = len(cf_recommendations) + len(content_recommendations)
            if total_candidates < n_items:
                print(f"⚠️  Too few candidates ({total_candidates}), using Simple Rules fallback")
                return self._simple_rules_recommendation(user_id, n_items, context)
            
            # If neither strategy is ready, use fallback
            if not cf_recommendations and not content_recommendations:
                print(f"❌ No strategies ready, using fallback")
                return self._fallback_recommendations(user_id, n_items, context)
            
            # Combine candidate products
            all_candidates = list(set(cf_recommendations + content_recommendations))
            
            # If we have candidates, score them with hybrid approach
            if all_candidates:
                scored_products = self._score_candidates(user_id, all_candidates, context)
                
                # Filter by minimum score threshold
                filtered_products = {
                    pid: score for pid, score in scored_products.items()
                    if score >= self.settings.SCORE_THRESHOLD
                }
                
                if not filtered_products:
                    # If filtering removed everything, use fallback
                    return self._fallback_recommendations(user_id, n_items, context)
                
                # Sort by hybrid score
                sorted_products = sorted(filtered_products.items(), key=lambda x: x[1], reverse=True)
                
                # Take more candidates for diversity (3x to ensure good diversity)
                candidate_count = min(len(sorted_products), n_items * 3)
                candidate_recommendations = [pid for pid, _ in sorted_products[:candidate_count]]
                
                # Apply diversity if we have enough candidates
                if len(candidate_recommendations) > n_items:
                    recommendations = self._apply_diversity(candidate_recommendations, n_items)
                else:
                    recommendations = candidate_recommendations[:n_items]
                
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
            
            # Adaptive weighting based on user history
            cf_weight, content_weight = self._get_adaptive_weights(user_id)
            
            # Compute hybrid scores with multiple signals
            hybrid_scores = {}
            for product_id in product_ids:
                cf_score = cf_scores.get(product_id, 0.0)
                content_score = content_scores.get(product_id, 0.0)
                
                # Base weighted combination
                hybrid_score = (
                    cf_weight * cf_score +
                    content_weight * content_score
                )
                
                # Consensus boost - both strategies agree
                if cf_score > 0.3 and content_score > 0.3:
                    hybrid_score *= 1.25  # Strong consensus
                elif cf_score > 0 and content_score > 0:
                    hybrid_score *= 1.1   # Weak consensus
                
                # Apply popularity factor from viewCount and clickCount
                popularity_factor = self._get_popularity_factor(product_id)
                hybrid_score *= (1.0 + popularity_factor * 0.15)  # Up to 15% boost
                
                # Quality boost from ratings
                quality_boost = self._get_quality_boost(product_id)
                hybrid_score *= (1.0 + quality_boost)
                
                hybrid_scores[product_id] = hybrid_score
            
            return hybrid_scores
            
        except Exception as e:
            print(f"Error scoring candidates: {e}")
            return {pid: 0.0 for pid in product_ids}
    
    def _get_adaptive_weights(self, user_id: str) -> tuple:
        """Adapt CF/Content weights based on user history"""
        try:
            if hasattr(self.product_repo, 'order_repo'):
                orders = self.product_repo.order_repo.find_many({'userId': user_id})
                order_count = len(orders)
                
                if order_count >= 5:
                    return (0.75, 0.25)  # Mature user - trust CF more
                elif order_count >= 2:
                    return (0.65, 0.35)  # Some history
                else:
                    return (0.5, 0.5)    # New user - equal weight
            return (self.cf_weight, self.content_weight)
        except:
            return (self.cf_weight, self.content_weight)
    
    def _get_quality_boost(self, product_id: str) -> float:
        """Get quality boost from rating signals"""
        try:
            product = self.product_repo.find_by_id(product_id)
            if not product:
                return 0.0
            
            avg_rating = product.get('averageRating', 0)
            total_ratings = product.get('totalRatings', 0)
            
            # Rating boost: 4+ stars get boost
            rating_boost = max(0, (avg_rating - 3.5) / 5.0) * 0.15
            
            # Review count boost: more reviews = more reliable
            review_boost = min(total_ratings / 20, 1.0) * 0.05
            
            return rating_boost + review_boost
        except:
            return 0.0
    
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
    
    def _get_popularity_factor(self, product_id: str) -> float:
        """Get popularity factor from viewCount and clickCount (0-1 scale)"""
        try:
            product = self.product_repo.find_by_id(product_id)
            if not product:
                return 0.0
            
            view_count = product.get('viewCount', 0)
            click_count = product.get('clickCount', 0)
            
            if view_count == 0 and click_count == 0:
                return 0.0
            
            # CTR quality signal
            ctr = (click_count / max(view_count, 1)) if view_count > 0 else 0
            normalized_ctr = min(ctr / 0.5, 1.0)  # Assume max CTR 50%
            
            # Engagement signal (log scale)
            total_engagement = view_count + click_count * 5  # clicks worth 5x views
            normalized_engagement = min(np.log1p(total_engagement) / np.log1p(5000), 1.0)
            
            # Combine: prioritize CTR quality
            popularity_factor = normalized_ctr * 0.7 + normalized_engagement * 0.3
            
            return float(popularity_factor)
            
        except Exception as e:
            print(f"Error getting popularity factor: {e}")
            return 0.0
    
    def _apply_diversity(self, product_ids: List[str], n_items: int) -> List[str]:
        """Apply diversity to avoid recommending too many similar products"""
        try:
            if len(product_ids) <= n_items:
                return product_ids
            
            diverse_recommendations = [product_ids[0]]  # Start with top product
            category_count = {}  # Track how many items from each category
            
            # Get category of first product
            first_product = self.product_repo.find_by_id(product_ids[0])
            if first_product and 'productCategory' in first_product:
                first_category = str(first_product['productCategory'])
                category_count[first_category] = 1
            
            # Define max items per category (enforce diversity)
            max_per_category = max(2, n_items // 2)  # At most 2 or 50% from same category
            
            # First pass: prioritize new categories
            for product_id in product_ids[1:]:
                if len(diverse_recommendations) >= n_items:
                    break
                
                product = self.product_repo.find_by_id(product_id)
                if not product:
                    continue
                
                category = str(product.get('productCategory', ''))
                current_count = category_count.get(category, 0)
                
                # Only add if category not maxed out
                if current_count < max_per_category:
                    diverse_recommendations.append(product_id)
                    category_count[category] = current_count + 1
            
            # Second pass: fill remaining slots if needed (relaxed constraint)
            if len(diverse_recommendations) < n_items:
                for product_id in product_ids:
                    if len(diverse_recommendations) >= n_items:
                        break
                    
                    if product_id not in diverse_recommendations:
                        diverse_recommendations.append(product_id)
            
            return diverse_recommendations
            
        except Exception as e:
            print(f"Error applying diversity: {e}")
            return product_ids[:n_items]
    
    def get_scores(self, user_id: str, product_ids: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Get hybrid scores for specific products"""
        return self._score_candidates(user_id, product_ids, context)
    
    def _simple_rules_recommendation(self, user_id: str, n_items: int, context: Optional[Dict[str, Any]]) -> List[str]:
        """Use Simple Rules when CF/Content fail - Guaranteed diverse recommendations"""
        try:
            print(f"🎲 Using Simple Rules recommendation engine")
            return self.simple_rules.recommend(user_id, n_items, context)
        except Exception as e:
            print(f"Error in simple rules: {e}")
            return self._fallback_recommendations(user_id, n_items, context)
    
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
    
    def _simple_rules_recommendation(self, user_id: str, n_items: int, context: Optional[Dict[str, Any]]) -> List[str]:
        """Simple rule-based recommendation when ML strategies fail"""
        try:
            print(f"🎲 Using Simple Rules Strategy...")
            from .simple_rules import SimpleRuleBasedRecommendation
            
            # Get order and rating repos
            order_repo = None
            rating_repo = None
            
            if hasattr(self, 'cf_strategy'):
                order_repo = self.cf_strategy.order_repo
                rating_repo = self.cf_strategy.rating_repo
            
            simple_rec = SimpleRuleBasedRecommendation(
                self.product_repo,
                order_repo,
                rating_repo
            )
            
            return simple_rec.recommend(user_id, n_items, context)
            
        except Exception as e:
            print(f"Error in simple rules: {e}")
            import traceback
            traceback.print_exc()
            # Last resort fallback
            return self._fallback_recommendations(user_id, n_items, context)
    
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
