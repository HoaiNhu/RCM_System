"""
Collaborative Filtering strategy using NMF
"""
import numpy as np
from typing import List, Optional, Dict, Any
from sklearn.decomposition import NMF
from datetime import datetime
import pickle
import os

from .base import IRecommendationStrategy, IModelTrainer
from ..repositories import (
    OrderRepository,
    RatingRepository,
    ProductRepository,
    SearchHistoryRepository,
    ModelMetadataRepository
)
from ..core.config import Settings


class CollaborativeFilteringStrategy(IRecommendationStrategy, IModelTrainer):
    """
    Collaborative Filtering using Non-negative Matrix Factorization (NMF)
    Follows Single Responsibility Principle - handles only CF recommendations
    """
    
    def __init__(
        self,
        order_repo: OrderRepository,
        rating_repo: RatingRepository,
        product_repo: ProductRepository,
        search_repo: SearchHistoryRepository,
        metadata_repo: ModelMetadataRepository,
        settings: Settings
    ):
        self.order_repo = order_repo
        self.rating_repo = rating_repo
        self.product_repo = product_repo
        self.search_repo = search_repo
        self.metadata_repo = metadata_repo
        self.settings = settings
        
        self.model: Optional[NMF] = None
        self.user_features: Optional[np.ndarray] = None
        self.product_features: Optional[np.ndarray] = None
        self.user_to_idx: Dict[str, int] = {}
        self.product_to_idx: Dict[str, int] = {}
        self.idx_to_product: Dict[int, str] = {}
        
        self._load_model()
    
    def _load_model(self) -> bool:
        """Load model from disk if available"""
        try:
            if os.path.exists(self.settings.MODEL_PATH):
                print(f"📂 Loading CF model from: {self.settings.MODEL_PATH}")
                with open(self.settings.MODEL_PATH, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data['model']
                    self.user_features = data['user_features']
                    self.product_features = data['product_features']
                    self.user_to_idx = data['user_to_idx']
                    self.product_to_idx = data['product_to_idx']
                    self.idx_to_product = {idx: pid for pid, idx in self.product_to_idx.items()}
                    print("      ✅ Collaborative filtering model loaded successfully")
                    print(f"      Users: {len(self.user_to_idx)}, Products: {len(self.product_to_idx)}")
                    return True
            else:
                print(f"ℹ️  CF model file not found: {self.settings.MODEL_PATH}")
                print("   Model will be trained on first use or you can manually train:")
                print("   POST http://localhost:8000/model/train")
        except Exception as e:
            print(f"⚠️  Could not load CF model: {e}")
        return False
    
    def _save_model(self) -> bool:
        """Save model to disk"""
        try:
            data = {
                'model': self.model,
                'user_features': self.user_features,
                'product_features': self.product_features,
                'user_to_idx': self.user_to_idx,
                'product_to_idx': self.product_to_idx
            }
            with open(self.settings.MODEL_PATH, 'wb') as f:
                pickle.dump(data, f)
            print("✓ Saved collaborative filtering model")
            return True
        except Exception as e:
            print(f"Error saving model: {e}")
            return False
    
    def _prepare_interaction_matrix(self, after_timestamp: Optional[datetime] = None) -> Optional[np.ndarray]:
        """Prepare user-item interaction matrix with search history integration"""
        try:
            # Get users and products
            users_orders = self.order_repo.get_users_with_orders(after_timestamp)
            users_ratings = self.rating_repo.get_users_with_ratings(after_timestamp)
            all_users = sorted(users_orders | users_ratings)
            
            # Get all products from orders and ratings
            products_set = set()
            for order in self.order_repo.find_many({} if not after_timestamp else {'createdAt': {'$gt': after_timestamp}}):
                for item in order.get('orderItems', []):
                    products_set.add(str(item['product']))
            
            for rating in self.rating_repo.find_many({} if not after_timestamp else {'createdAt': {'$gt': after_timestamp}}):
                if rating.get('productId'):
                    products_set.add(str(rating['productId']))
            
            all_products = sorted(products_set)
            
            if not all_users or not all_products:
                print("Insufficient data for matrix")
                return None
            
            print(f"Building matrix: {len(all_users)} users × {len(all_products)} products")
            
            # Create mappings
            self.user_to_idx = {uid: idx for idx, uid in enumerate(all_users)}
            self.product_to_idx = {pid: idx for idx, pid in enumerate(all_products)}
            self.idx_to_product = {idx: pid for pid, idx in self.product_to_idx.items()}
            
            # Initialize matrix
            n_users = len(all_users)
            n_products = len(all_products)
            interactions = np.zeros((n_users, n_products))
            
            # Add order interactions (weight: 2.0 per quantity)
            print("Processing orders...")
            query = {} if not after_timestamp else {'createdAt': {'$gt': after_timestamp}}
            for order in self.order_repo.find_many(query):
                user_id = str(order.get('userId', ''))
                if user_id not in self.user_to_idx:
                    continue
                user_idx = self.user_to_idx[user_id]
                
                for item in order.get('orderItems', []):
                    product_id = str(item['product'])
                    if product_id not in self.product_to_idx:
                        continue
                    product_idx = self.product_to_idx[product_id]
                    quantity = item.get('quantity', 1)
                    interactions[user_idx, product_idx] += quantity * 2.0
            
            # Add rating interactions (weighted by rating and comment sentiment)
            for rating in self.rating_repo.find_many(query):
                user_id = str(rating.get('userId', ''))
                product_id = str(rating.get('productId', ''))
                
                if user_id not in self.user_to_idx or product_id not in self.product_to_idx:
                    continue
                
                user_idx = self.user_to_idx[user_id]
                product_idx = self.product_to_idx[product_id]
                
                rating_value = rating.get('rating', 0)
                comment = rating.get('comment', '')
                comment_score = self._analyze_sentiment(comment)
                
                weight = rating_value * 0.6 + comment_score * 0.4
                interactions[user_idx, product_idx] += max(weight, 0)
            
            # Integrate search history (NEW - increase weight for searched products)
            print("Integrating search history...")
            for user_id in all_users:
                if user_id not in self.user_to_idx:
                    continue
                user_idx = self.user_to_idx[user_id]
                
                # Get searched product IDs
                searched_products = self.search_repo.get_searched_product_ids(user_id)
                for product_id in searched_products:
                    if product_id in self.product_to_idx:
                        product_idx = self.product_to_idx[product_id]
                        # Add search weight (0.5 per search)
                        interactions[user_idx, product_idx] += 0.5
            
            # Normalize to 0-5 scale
            max_val = interactions.max()
            if max_val > 0:
                interactions = interactions / max_val * 5.0
            
            print(f"Matrix prepared: {np.count_nonzero(interactions)} non-zero interactions")
            return interactions
            
        except Exception as e:
            print(f"Error preparing interaction matrix: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _analyze_sentiment(self, comment: str) -> float:
        """Analyze comment sentiment"""
        if not comment or not isinstance(comment, str):
            return 0
        
        comment = comment.lower()
        positive_words = {'tốt', 'ngon', 'tuyệt', 'xuất sắc', 'hài lòng', 'thích', 'đẹp', 'chất lượng'}
        negative_words = {'tệ', 'dở', 'kém', 'không ngon', 'tồi', 'không thích', 'xấu'}
        
        positive = sum(1 for word in positive_words if word in comment)
        negative = sum(1 for word in negative_words if word in comment)
        return positive - negative
    
    def train(self, force_retrain: bool = False) -> bool:
        """Train NMF model"""
        try:
            print("\n" + "="*60)
            print("[1/4] 📊 TRAINING COLLABORATIVE FILTERING MODEL")
            print("="*60)
            print(f"      Force retrain: {force_retrain}")
            print(f"      Model path: {self.settings.MODEL_PATH}")
            
            # Check if model exists and not forcing retrain
            if not force_retrain and self.is_ready():
                print("\n✅ CF model already loaded and ready!")
                return True
            
            # Prepare data
            print("\n[2/4] 🔄 Preparing interaction matrix...")
            interactions = self._prepare_interaction_matrix()
            if interactions is None:
                print("❌ Failed: Insufficient data")
                return False
            
            # Train NMF
            n_components = min(self.settings.N_COMPONENTS, min(interactions.shape) - 1)
            print(f"[3/4] 🤖 Training NMF model...")
            print(f"      Components: {n_components}, Max iterations: {self.settings.MAX_ITER}")
            
            import time
            start_time = time.time()
            
            self.model = NMF(
                n_components=n_components,
                init='nndsvd',
                random_state=42,
                max_iter=self.settings.MAX_ITER,
                alpha_W=0.01,
                alpha_H=0.01,
                l1_ratio=0.5,
                verbose=0,
                tol=1e-3
            )
            
            self.user_features = self.model.fit_transform(interactions)
            self.product_features = self.model.components_
            
            train_time = time.time() - start_time
            
            print(f"      ✅ Training completed in {train_time:.2f}s")
            print(f"      Iterations: {self.model.n_iter_}")
            print(f"      Users: {self.user_features.shape[0]}, Products: {self.product_features.shape[1]}")
            print(f"      Reconstruction error: {self.model.reconstruction_err_:.4f}")
            
            # Save model
            print("[4/4] 💾 Saving model...")
            self._save_model()
            self.metadata_repo.update_last_update()
            print("      ✅ Model saved successfully")
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            print(f"Error training model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def evaluate(self) -> Dict[str, float]:
        """Evaluate model using precision, recall, F1 - ONLY on real data"""
        try:
            if not self.is_ready():
                return {'precision': 0, 'recall': 0, 'f1': 0}
            
            # Get ALL test orders but EXCLUDE synthetic data from evaluation
            test_orders = self.order_repo.get_recent_test_orders(0.2)  # Increased to 20% for better evaluation
            # Filter out synthetic orders - only evaluate on real user behavior
            real_test_orders = [order for order in test_orders if not order.get('synthetic', False)]
            
            if not real_test_orders:
                print("⚠️  No real orders for evaluation, using all orders as fallback")
                real_test_orders = test_orders
            
            print(f"📊 Evaluating on {len(real_test_orders)} real orders (excluded {len(test_orders) - len(real_test_orders)} synthetic)")
            
            precisions = []
            recalls = []
            
            for order in real_test_orders:
                user_id = str(order.get('userId', ''))
                if user_id not in self.user_to_idx:
                    continue
                
                actual_items = set(str(item['product']) for item in order.get('orderItems', []))
                if not actual_items:
                    continue
                    
                # Get more recommendations for better evaluation
                recommended = self.recommend(user_id, n_items=10)
                
                if not recommended:
                    continue
                
                relevant = actual_items & set(recommended)
                precision = len(relevant) / len(recommended)
                recall = len(relevant) / len(actual_items)
                
                precisions.append(precision)
                recalls.append(recall)
            
            avg_precision = np.mean(precisions) if precisions else 0
            avg_recall = np.mean(recalls) if recalls else 0
            f1 = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0
            
            print(f"✅ Evaluation: Precision={avg_precision:.4f}, Recall={avg_recall:.4f}, F1={f1:.4f}")
            
            return {
                'precision': float(avg_precision),
                'recall': float(avg_recall),
                'f1': float(f1)
            }
            
        except Exception as e:
            print(f"Error evaluating model: {e}")
            return {'precision': 0, 'recall': 0, 'f1': 0}
    
    def recommend(self, user_id: str, n_items: int = 5, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Generate recommendations using collaborative filtering"""
        try:
            if not self.is_ready():
                return []
            
            if user_id not in self.user_to_idx:
                return []  # User not in training set
            
            # Get user features and compute scores
            user_idx = self.user_to_idx[user_id]
            user_vec = self.user_features[user_idx]
            scores = user_vec @ self.product_features
            
            # Get top products
            top_indices = np.argsort(-scores)
            
            # Filter and collect recommendations
            recommendations = []
            current_product_id = context.get('current_product_id') if context else None
            
            for idx in top_indices:
                if len(recommendations) >= n_items:
                    break
                
                product_id = self.idx_to_product[idx]
                
                # Skip current product
                if current_product_id and product_id == current_product_id:
                    continue
                
                # Verify product exists and has good rating
                product = self.product_repo.find_by_id(product_id)
                if product and product.get('averageRating', 0) >= self.settings.MIN_RATING_THRESHOLD:
                    recommendations.append(product_id)
            
            return recommendations
            
        except Exception as e:
            print(f"Error in CF recommend: {e}")
            return []
    
    def get_scores(self, user_id: str, product_ids: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Get CF scores for specific products"""
        try:
            if not self.is_ready() or user_id not in self.user_to_idx:
                return {pid: 0.0 for pid in product_ids}
            
            user_idx = self.user_to_idx[user_id]
            user_vec = self.user_features[user_idx]
            
            scores = {}
            for product_id in product_ids:
                if product_id in self.product_to_idx:
                    product_idx = self.product_to_idx[product_id]
                    product_vec = self.product_features[:, product_idx]
                    score = float(user_vec @ product_vec)
                    scores[product_id] = score
                else:
                    scores[product_id] = 0.0
            
            return scores
            
        except Exception as e:
            print(f"Error getting CF scores: {e}")
            return {pid: 0.0 for pid in product_ids}
    
    def is_ready(self) -> bool:
        """Check if model is ready"""
        return (
            self.model is not None and
            self.user_features is not None and
            self.product_features is not None and
            len(self.user_to_idx) > 0 and
            len(self.product_to_idx) > 0
        )
