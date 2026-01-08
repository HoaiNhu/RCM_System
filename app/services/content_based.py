"""
Content-Based Filtering strategy using TF-IDF and cosine similarity
"""
import numpy as np
from typing import List, Optional, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os

from .base import IRecommendationStrategy
from ..repositories import ProductRepository, SearchHistoryRepository
from ..core.config import Settings


class ContentBasedFilteringStrategy(IRecommendationStrategy):
    """
    Content-Based Filtering using TF-IDF for text features and cosine similarity
    Follows Single Responsibility Principle - handles only content-based recommendations
    """
    
    def __init__(
        self,
        product_repo: ProductRepository,
        search_repo: SearchHistoryRepository,
        settings: Settings
    ):
        self.product_repo = product_repo
        self.search_repo = search_repo
        self.settings = settings
        
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.product_vectors: Optional[np.ndarray] = None
        self.product_ids: List[str] = []
        self.product_to_idx: Dict[str, int] = {}
        
        self._build_content_features()
    
    def _build_content_features(self) -> bool:
        """Build TF-IDF features for all products"""
        try:
            print("\n" + "="*60)
            print("[1/3] 📝 BUILDING CONTENT-BASED FEATURES")
            print("="*60)
            
            # Get all products
            print("[2/3] 📦 Loading products from database...")
            products = self.product_repo.find_many({}, limit=None)
            if not products:
                print("❌ No products found")
                return False
            
            print(f"      Found {len(products)} products")
            
            # Extract text features
            self.product_ids = []
            documents = []
            
            for product in products:
                product_id = str(product['_id'])
                self.product_ids.append(product_id)
                
                # Combine name, description, and category
                name = product.get('name', '')
                description = product.get('description', '')
                category = str(product.get('productCategory', ''))
                
                # Create document (weight name more than description)
                document = f"{name} {name} {description} {category}"
                documents.append(document)
            
            # Create mappings
            self.product_to_idx = {pid: idx for idx, pid in enumerate(self.product_ids)}
            
            # Build TF-IDF vectors (improved for small dataset)
            self.vectorizer = TfidfVectorizer(
                max_features=500,  # Increased for better feature extraction
                stop_words=None,  # Keep all words for small Vietnamese dataset
                ngram_range=(1, 2),  # Use bigrams for better context
                min_df=1,  # Keep all words (small dataset)
                max_df=1.0,  # No upper limit (small dataset)
                token_pattern=r'(?u)\b\w+\b'  # Better Vietnamese tokenization
            )
            
            print("[3/3] 🔨 Building TF-IDF vectors...")
            self.product_vectors = self.vectorizer.fit_transform(documents).toarray()
            
            print(f"      ✅ Content features built: {self.product_vectors.shape}")
            print(f"      Vocabulary size: {len(self.vectorizer.vocabulary_)}")
            print("="*60 + "\n")
            return True
            
        except Exception as e:
            print(f"Error building content features: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def recommend(self, user_id: str, n_items: int = 5, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Generate content-based recommendations"""
        try:
            if not self.is_ready():
                return []
            
            # Get reference product for similarity
            current_product_id = context.get('current_product_id') if context else None
            
            if current_product_id and current_product_id in self.product_to_idx:
                # Recommend similar to current product
                return self._recommend_similar(current_product_id, n_items)
            else:
                # Use search history to find user preferences
                return self._recommend_from_search_history(user_id, n_items)
            
        except Exception as e:
            print(f"Error in content-based recommend: {e}")
            return []
    
    def _recommend_similar(self, product_id: str, n_items: int) -> List[str]:
        """Recommend products similar to given product"""
        try:
            if product_id not in self.product_to_idx:
                return []
            
            # Get product vector
            product_idx = self.product_to_idx[product_id]
            product_vec = self.product_vectors[product_idx].reshape(1, -1)
            
            # Compute cosine similarity with all products
            similarities = cosine_similarity(product_vec, self.product_vectors)[0]
            
            # Get top similar products (excluding itself)
            top_indices = np.argsort(-similarities)
            
            recommendations = []
            for idx in top_indices:
                if len(recommendations) >= n_items:
                    break
                
                similar_product_id = self.product_ids[idx]
                
                # Skip the same product
                if similar_product_id == product_id:
                    continue
                
                # Apply similarity threshold (NEW)
                if similarities[idx] < 0.2:  # Reduced from 0.3 for better recall
                    continue
                
                # Verify product quality with stricter criteria
                product = self.product_repo.find_by_id(similar_product_id)
                if not product:
                    continue
                
                avg_rating = product.get('averageRating', 0)
                total_ratings = product.get('totalRatings', 0)
                
                # Apply quality thresholds
                if (avg_rating >= self.settings.MIN_RATING_THRESHOLD and
                    total_ratings >= self.settings.MIN_TOTAL_RATINGS):
                    recommendations.append(similar_product_id)
            
            return recommendations
            
        except Exception as e:
            print(f"Error recommending similar: {e}")
            return []
    
    def _get_diverse_products(self, exclude_product_id: str, n_items: int) -> List[str]:
        """Get diverse products from DIFFERENT categories - maximum 1 per category"""
        try:
            current_product = self.product_repo.find_by_id(exclude_product_id)
            current_category = str(current_product.get('productCategory', '')) if current_product else None
            
            # Group products by category (excluding current category)
            category_products = {}
            
            for product_id in self.product_ids:
                if product_id == exclude_product_id:
                    continue
                
                product = self.product_repo.find_by_id(product_id)
                if not product:
                    continue
                
                category = str(product.get('productCategory', ''))
                
                # Skip same category to ensure diversity
                if current_category and category == current_category:
                    continue
                
                if category not in category_products:
                    category_products[category] = []
                
                category_products[category].append({
                    'id': product_id,
                    'rating': product.get('averageRating', 0)
                })
            
            # Take 1 best product from each different category
            diverse = []
            for cat, products in sorted(category_products.items(), key=lambda x: len(x[1]), reverse=True):
                if len(diverse) >= n_items:
                    break
                if products:
                    best = max(products, key=lambda x: x['rating'])
                    diverse.append(best['id'])
            
            print(f"🎨 Diverse: {len(diverse)} products from {len(category_products)} categories")
            return diverse
            
        except Exception as e:
            print(f"Error getting diverse products: {e}")
            return []
    
    def _recommend_from_search_history(self, user_id: str, n_items: int) -> List[str]:
        """Recommend products based on user's search history"""
        try:
            # Get user's search keywords
            keywords = self.search_repo.get_search_keywords(user_id)
            
            if not keywords:
                return []
            
            # Create query vector from keywords
            query_text = ' '.join(keywords)
            query_vec = self.vectorizer.transform([query_text]).toarray()
            
            # Compute similarity with all products
            similarities = cosine_similarity(query_vec, self.product_vectors)[0]
            
            # Get top products with similarity threshold
            top_indices = np.argsort(-similarities)
            
            recommendations = []
            for idx in top_indices:
                if len(recommendations) >= n_items:
                    break
                
                # Apply similarity threshold
                if similarities[idx] < 0.15:  # Reduced for better recall
                    continue
                
                product_id = self.product_ids[idx]
                product = self.product_repo.find_by_id(product_id)
                
                if not product:
                    continue
                
                avg_rating = product.get('averageRating', 0)
                total_ratings = product.get('totalRatings', 0)
                
                # Apply quality filters
                if (avg_rating >= self.settings.MIN_RATING_THRESHOLD and
                    total_ratings >= self.settings.MIN_TOTAL_RATINGS):
                    recommendations.append(product_id)
            
            return recommendations
            
        except Exception as e:
            print(f"Error recommending from search history: {e}")
            return []
    
    def get_scores(self, user_id: str, product_ids: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Get content-based scores for specific products"""
        try:
            if not self.is_ready():
                return {pid: 0.0 for pid in product_ids}
            
            # Get reference product or use search history
            current_product_id = context.get('current_product_id') if context else None
            
            # Learn user's category preferences
            category_affinity = self._get_category_affinity(user_id)
            
            if current_product_id and current_product_id in self.product_to_idx:
                # Score based on similarity to current product
                scores = self._score_by_similarity(current_product_id, product_ids)
            else:
                # Score based on search history
                scores = self._score_by_search_history(user_id, product_ids)
            
            # Apply category affinity boost
            for product_id in product_ids:
                product = self.product_repo.find_by_id(product_id)
                if product and 'productCategory' in product:
                    category = str(product['productCategory'])
                    affinity = category_affinity.get(category, 0.0)
                    # Boost score by up to 20% based on category preference
                    scores[product_id] = scores.get(product_id, 0.0) * (1.0 + affinity * 0.2)
            
            return scores
            
        except Exception as e:
            print(f"Error getting content-based scores: {e}")
            return {pid: 0.0 for pid in product_ids}
    
    def _get_category_affinity(self, user_id: str) -> Dict[str, float]:
        """Learn user's category preferences from order history"""
        try:
            from collections import Counter
            from ..repositories import OrderRepository
            
            # Get user's orders
            orders = self.product_repo.order_repo.find_many({'userId': user_id}) if hasattr(self.product_repo, 'order_repo') else []
            
            category_counts = Counter()
            total_items = 0
            
            for order in orders:
                for item in order.get('orderItems', []):
                    product_id = str(item.get('product', ''))
                    product = self.product_repo.find_by_id(product_id)
                    if product and 'productCategory' in product:
                        category = str(product['productCategory'])
                        quantity = item.get('quantity', 1)
                        category_counts[category] += quantity
                        total_items += quantity
            
            # Normalize to 0-1 scores
            if total_items > 0:
                return {cat: count / total_items for cat, count in category_counts.items()}
            
            return {}
            
        except Exception as e:
            return {}
    
    def _score_by_similarity(self, reference_product_id: str, product_ids: List[str]) -> Dict[str, float]:
        """Score products by similarity to reference product"""
        try:
            ref_idx = self.product_to_idx[reference_product_id]
            ref_vec = self.product_vectors[ref_idx].reshape(1, -1)
            
            scores = {}
            for product_id in product_ids:
                if product_id in self.product_to_idx:
                    prod_idx = self.product_to_idx[product_id]
                    prod_vec = self.product_vectors[prod_idx].reshape(1, -1)
                    similarity = cosine_similarity(ref_vec, prod_vec)[0][0]
                    
                    # Apply popularity boost from viewCount and clickCount
                    popularity_boost = self._calculate_popularity_boost(product_id)
                    
                    # Combine similarity with popularity (70% similarity, 30% popularity)
                    final_score = similarity * 0.7 + popularity_boost * 0.3
                    scores[product_id] = float(final_score)
                else:
                    scores[product_id] = 0.0
            
            return scores
            
        except Exception as e:
            print(f"Error scoring by similarity: {e}")
            return {pid: 0.0 for pid in product_ids}
    
    def _score_by_search_history(self, user_id: str, product_ids: List[str]) -> Dict[str, float]:
        """Score products based on user's search history"""
        try:
            keywords = self.search_repo.get_search_keywords(user_id)
            
            if not keywords:
                return {pid: 0.0 for pid in product_ids}
            
            query_text = ' '.join(keywords)
            query_vec = self.vectorizer.transform([query_text]).toarray()
            
            scores = {}
            for product_id in product_ids:
                if product_id in self.product_to_idx:
                    prod_idx = self.product_to_idx[product_id]
                    prod_vec = self.product_vectors[prod_idx].reshape(1, -1)
                    similarity = cosine_similarity(query_vec, prod_vec)[0][0]
                    
                    # Apply popularity boost from viewCount and clickCount
                    popularity_boost = self._calculate_popularity_boost(product_id)
                    
                    # Combine similarity with popularity (70% similarity, 30% popularity)
                    final_score = similarity * 0.7 + popularity_boost * 0.3
                    scores[product_id] = float(final_score)
                else:
                    scores[product_id] = 0.0
            
            return scores
            
        except Exception as e:
            print(f"Error scoring by search history: {e}")
            return {pid: 0.0 for pid in product_ids}
    
    def _calculate_popularity_boost(self, product_id: str) -> float:
        """Calculate popularity boost from viewCount and clickCount"""
        try:
            product = self.product_repo.find_by_id(product_id)
            if not product:
                return 0.0
            
            view_count = product.get('viewCount', 0)
            click_count = product.get('clickCount', 0)
            
            if view_count == 0 and click_count == 0:
                return 0.0
            
            # Calculate CTR (Click-Through Rate) - chất lượng tương tác
            ctr = (click_count / max(view_count, 1)) if view_count > 0 else 0
            
            # Normalize CTR to 0-1 (assume max CTR is 0.5 or 50%)
            normalized_ctr = min(ctr / 0.5, 1.0)
            
            # Normalize view count using log scale (prevent viral products from dominating)
            # Assume 1000 views is very popular
            normalized_views = min(np.log1p(view_count) / np.log1p(1000), 1.0)
            
            # Combine: CTR is more important than absolute views
            # 60% CTR quality + 40% popularity
            popularity_score = normalized_ctr * 0.6 + normalized_views * 0.4
            
            return float(popularity_score)
            
        except Exception as e:
            print(f"Error calculating popularity boost: {e}")
            return 0.0
    
    def is_ready(self) -> bool:
        """Check if content-based strategy is ready"""
        return (
            self.vectorizer is not None and
            self.product_vectors is not None and
            len(self.product_ids) > 0
        )
