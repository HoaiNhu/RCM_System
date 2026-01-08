"""
SIMPLE RULE-BASED RECOMMENDATION - No ML, Just Smart Rules
Đảm bảo diversity bằng logic đơn giản
"""
from typing import List, Dict, Optional, Any
from collections import defaultdict
import random

class SimpleRuleBasedRecommendation:
    """
    Simple rule-based recommendation với category diversity
    KHÔNG cần ML model, chỉ dùng rules thông minh
    """
    
    def __init__(self, product_repo, order_repo, rating_repo):
        self.product_repo = product_repo
        self.order_repo = order_repo
        self.rating_repo = rating_repo
    
    def recommend(self, user_id: str, n_items: int = 5, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate diverse recommendations using simple rules
        """
        try:
            current_product_id = context.get('current_product_id') if context else None
            
            # Strategy: Mix 3 sources for maximum diversity
            # 1. User's purchase history (collaborative signal)
            # 2. Similar products (content signal) 
            # 3. Popular products from OTHER categories (diversity)
            
            recommendations = []
            category_count = defaultdict(int)
            current_category = None
            
            # Get current product category
            if current_product_id:
                current_product = self.product_repo.find_by_id(current_product_id)
                if current_product:
                    current_category = str(current_product.get('productCategory', ''))
            
            # Source 1: Products from user's purchase history (if available)
            user_history = self._get_user_purchased_products(user_id)
            if user_history:
                # Get products similar to what user bought before
                for hist_pid in user_history[:3]:  # Take top 3 from history
                    similar = self._get_similar_products(hist_pid, exclude_ids=[current_product_id] + recommendations)
                    for sim_pid in similar:
                        if len(recommendations) >= n_items:
                            break
                        
                        p = self.product_repo.find_by_id(sim_pid)
                        if not p:
                            continue
                        
                        cat = str(p.get('productCategory', ''))
                        # Limit 2 per category
                        if category_count[cat] < 2:
                            recommendations.append(sim_pid)
                            category_count[cat] += 1
            
            # Source 2: 1-2 products from SAME category as current (if any)
            if current_product_id and current_category and len(recommendations) < n_items:
                same_cat_products = self.product_repo.get_by_category(current_category, limit=5)
                for p in same_cat_products:
                    pid = str(p['_id'])
                    if pid == current_product_id or pid in recommendations:
                        continue
                    
                    if len(recommendations) >= n_items:
                        break
                    
                    # Max 2 from same category
                    if category_count[current_category] < 2:
                        recommendations.append(pid)
                        category_count[current_category] += 1
            
            # Source 3: Popular products from DIFFERENT categories (for diversity)
            if len(recommendations) < n_items:
                all_popular = self.product_repo.get_popular_products(limit=50, min_rating=2.0)
                
                # Group by category
                cat_products = defaultdict(list)
                for p in all_popular:
                    pid = str(p['_id'])
                    if pid == current_product_id or pid in recommendations:
                        continue
                    cat = str(p.get('productCategory', ''))
                    cat_products[cat].append(pid)
                
                # Round-robin: Take 1 from each category
                categories = [cat for cat in cat_products.keys() if cat != current_category]
                random.shuffle(categories)  # Randomize for variety
                
                for cat in categories:
                    if len(recommendations) >= n_items:
                        break
                    
                    # Max 2 per category
                    if category_count[cat] < 2 and cat_products[cat]:
                        recommendations.append(cat_products[cat][0])
                        category_count[cat] += 1
            
            # Fill remaining with any good products
            if len(recommendations) < n_items:
                all_products = self.product_repo.get_popular_products(limit=100, min_rating=2.0)
                for p in all_products:
                    pid = str(p['_id'])
                    if pid not in recommendations and pid != current_product_id:
                        recommendations.append(pid)
                        if len(recommendations) >= n_items:
                            break
            
            print(f"✅ Simple Rules: {len(recommendations)} items from {len(category_count)} categories")
            for cat, count in category_count.items():
                print(f"   └─ Category {cat[:8]}...: {count} items")
            
            return recommendations[:n_items]
            
        except Exception as e:
            print(f"Error in simple recommendation: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_user_purchased_products(self, user_id: str) -> List[str]:
        """Get products user has purchased before"""
        try:
            orders = self.order_repo.find_many({'userId': user_id}, limit=10)
            product_ids = []
            for order in orders:
                for item in order.get('orderItems', []):
                    pid = str(item.get('product', ''))
                    if pid:
                        product_ids.append(pid)
            return list(set(product_ids))[:5]  # Return unique, max 5
        except:
            return []
    
    def _get_similar_products(self, product_id: str, exclude_ids: List[str] = None) -> List[str]:
        """Get products similar to given product (same category + good rating)"""
        try:
            exclude_ids = exclude_ids or []
            product = self.product_repo.find_by_id(product_id)
            if not product:
                return []
            
            category = str(product.get('productCategory', ''))
            if not category:
                return []
            
            # Get products from same category with good ratings
            similar_products = self.product_repo.get_by_category(category, limit=10)
            result = []
            for p in similar_products:
                pid = str(p['_id'])
                if pid != product_id and pid not in exclude_ids:
                    if p.get('averageRating', 0) >= 2.5:
                        result.append(pid)
            
            return result[:5]
        except:
            return []
