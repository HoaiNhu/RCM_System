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
            
            # Build TF-IDF vectors (optimized for speed)
            self.vectorizer = TfidfVectorizer(
                max_features=200,  # Reduced from 500 for faster processing
                stop_words=None,
                ngram_range=(1, 1),  # Only unigrams for speed
                min_df=1,
                max_df=0.8
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
                
                # Verify product quality
                product = self.product_repo.find_by_id(similar_product_id)
                if product and product.get('averageRating', 0) >= self.settings.MIN_RATING_THRESHOLD:
                    recommendations.append(similar_product_id)
            
            return recommendations
            
        except Exception as e:
            print(f"Error recommending similar: {e}")
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
            
            # Get top products
            top_indices = np.argsort(-similarities)[:n_items * 2]
            
            recommendations = []
            for idx in top_indices:
                if len(recommendations) >= n_items:
                    break
                
                product_id = self.product_ids[idx]
                product = self.product_repo.find_by_id(product_id)
                
                if product and product.get('averageRating', 0) >= self.settings.MIN_RATING_THRESHOLD:
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
            
            if current_product_id and current_product_id in self.product_to_idx:
                # Score based on similarity to current product
                return self._score_by_similarity(current_product_id, product_ids)
            else:
                # Score based on search history
                return self._score_by_search_history(user_id, product_ids)
            
        except Exception as e:
            print(f"Error getting content-based scores: {e}")
            return {pid: 0.0 for pid in product_ids}
    
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
                    scores[product_id] = float(similarity)
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
                    scores[product_id] = float(similarity)
                else:
                    scores[product_id] = 0.0
            
            return scores
            
        except Exception as e:
            print(f"Error scoring by search history: {e}")
            return {pid: 0.0 for pid in product_ids}
    
    def is_ready(self) -> bool:
        """Check if content-based strategy is ready"""
        return (
            self.vectorizer is not None and
            self.product_vectors is not None and
            len(self.product_ids) > 0
        )
