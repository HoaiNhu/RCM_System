"""
Concrete repository implementations for specific collections
"""
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from .base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for users collection"""
    
    def __init__(self, db):
        super().__init__(db, 'users')
    
    def get_active_users(self) -> List[str]:
        """Get list of active user IDs"""
        users = self.find_many({}, limit=None)
        return [str(user['_id']) for user in users]


class ProductRepository(BaseRepository):
    """Repository for products collection"""
    
    def __init__(self, db):
        super().__init__(db, 'products')
    
    def get_by_category(self, category_id: str, limit: int = 10) -> List[Dict]:
        """Get products by category, sorted by rating"""
        return self.find_many(
            {'productCategory': category_id},
            limit=limit,
            sort=[('averageRating', -1), ('totalRatings', -1)]
        )
    
    def get_popular_products(self, limit: int = 10, min_rating: float = 2.0) -> List[Dict]:
        """Get popular products sorted by rating and reviews"""
        return self.find_many(
            {'averageRating': {'$gte': min_rating}},
            limit=limit,
            sort=[('averageRating', -1), ('totalRatings', -1)]
        )
    
    def search_by_keywords(self, keywords: List[str], limit: int = 20) -> List[Dict]:
        """Search products by keywords in name and description"""
        if not keywords:
            return []
        
        query = {
            '$or': [
                {'name': {'$regex': k, '$options': 'i'}} for k in keywords
            ] + [
                {'description': {'$regex': k, '$options': 'i'}} for k in keywords
            ]
        }
        return self.find_many(query, limit=limit, sort=[('averageRating', -1)])
    
    def get_product_features(self, product_id: str) -> Optional[Dict]:
        """Get product features for content-based filtering"""
        product = self.find_by_id(product_id)
        if not product:
            return None
        
        return {
            'name': product.get('name', ''),
            'description': product.get('description', ''),
            'category': str(product.get('productCategory', '')),
            'price': product.get('price', 0),
            'rating': product.get('averageRating', 0)
        }


class OrderRepository(BaseRepository):
    """Repository for orders collection"""
    
    def __init__(self, db):
        super().__init__(db, 'orders')
    
    def get_user_orders(self, user_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Get all orders for a user"""
        return self.find_many({'userId': user_id}, limit=limit, sort=[('createdAt', -1)])
    
    def get_users_with_orders(self, after_timestamp: Optional[datetime] = None) -> Set[str]:
        """Get set of user IDs who have placed orders"""
        query = {}
        if after_timestamp:
            query['createdAt'] = {'$gt': after_timestamp}
        
        orders = self.find_many(query, limit=None)
        return set(str(order['userId']) for order in orders if order.get('userId'))
    
    def get_order_products(self, user_id: str) -> List[str]:
        """Get all product IDs ordered by user"""
        orders = self.get_user_orders(user_id)
        products = []
        for order in orders:
            for item in order.get('orderItems', []):
                products.append(str(item['product']))
        return products
    
    def get_recent_test_orders(self, test_size_ratio: float = 0.1) -> List[Dict]:
        """Get recent orders for testing/evaluation"""
        all_orders = self.find_many({}, sort=[('createdAt', -1)])
        test_size = max(1, int(test_size_ratio * len(all_orders)))
        return all_orders[:test_size]


class RatingRepository(BaseRepository):
    """Repository for ratings collection"""
    
    def __init__(self, db):
        super().__init__(db, 'ratings')
    
    def get_user_ratings(self, user_id: str) -> List[Dict]:
        """Get all ratings by user"""
        return self.find_many({'userId': user_id})
    
    def get_product_ratings(self, product_id: str) -> List[Dict]:
        """Get all ratings for a product"""
        return self.find_many({'productId': product_id})
    
    def get_users_with_ratings(self, after_timestamp: Optional[datetime] = None) -> Set[str]:
        """Get set of user IDs who have rated products"""
        query = {}
        if after_timestamp:
            query['createdAt'] = {'$gt': after_timestamp}
        
        ratings = self.find_many(query, limit=None)
        return set(str(rating['userId']) for rating in ratings if rating.get('userId'))


class SearchHistoryRepository(BaseRepository):
    """Repository for search history collection"""
    
    def __init__(self, db):
        super().__init__(db, 'searchHistory')
    
    def get_user_searches(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user's search history"""
        return self.find_many({'userId': user_id}, limit=limit, sort=[('createdAt', -1)])
    
    def get_search_keywords(self, user_id: str) -> List[str]:
        """Extract keywords from user's search history"""
        searches = self.get_user_searches(user_id)
        keywords = []
        for search in searches:
            query = search.get('searchQuery', '').lower()
            if query:
                keywords.extend(query.split())
        return list(set(keywords))  # Unique keywords
    
    def get_searched_product_ids(self, user_id: str) -> Set[str]:
        """Get product IDs user has searched for"""
        searches = self.get_user_searches(user_id)
        product_ids = set()
        for search in searches:
            # If search result contains product IDs
            results = search.get('results', [])
            for result in results:
                if isinstance(result, dict) and 'productId' in result:
                    product_ids.add(str(result['productId']))
        return product_ids
    
    def log_search(self, user_id: str, query: str, results: List[Dict]) -> str:
        """Log a new search"""
        document = {
            'userId': user_id,
            'searchQuery': query,
            'results': results,
            'createdAt': datetime.utcnow()
        }
        return self.insert_one(document)


class QuizResponseRepository(BaseRepository):
    """Repository for quiz responses"""
    
    def __init__(self, db):
        super().__init__(db, 'quiz_responses')
    
    def get_user_session_responses(self, user_id: str, session_id: str) -> List[Dict]:
        """Get quiz responses for a session"""
        return self.find_many({
            'userId': user_id,
            'sessionId': session_id,
            'completed': True
        })


class QuizRepository(BaseRepository):
    """Repository for quizzes"""
    
    def __init__(self, db):
        super().__init__(db, 'quizzes')


class ModelMetadataRepository(BaseRepository):
    """Repository for model metadata"""
    
    def __init__(self, db):
        super().__init__(db, 'model_metadata')
    
    def get_last_update_timestamp(self) -> Optional[datetime]:
        """Get last model update timestamp"""
        metadata = self.find_one({'type': 'last_update'})
        return metadata.get('timestamp') if metadata else None
    
    def update_last_update(self) -> bool:
        """Update last model update timestamp"""
        return self.update_one(
            {'type': 'last_update'},
            {'$set': {'timestamp': datetime.utcnow()}},
            upsert=True
        )


class RecommendationRepository(BaseRepository):
    """Repository for cached recommendations"""
    
    def __init__(self, db):
        super().__init__(db, 'recommendations')
    
    def get_cached_recommendations(self, user_id: str) -> Optional[List[str]]:
        """Get cached recommendations for user"""
        doc = self.find_one({'userId': user_id})
        return doc.get('recommended') if doc else None
    
    def cache_recommendations(self, user_id: str, recommendations: List[str]) -> bool:
        """Cache recommendations for user"""
        return self.update_one(
            {'userId': user_id},
            {'$set': {'recommended': recommendations, 'updatedAt': datetime.utcnow()}},
            upsert=True
        )
