"""
Business Rules to enhance recommendations without complex AI
Perfect for academic projects - easy to explain and effective
"""
from typing import List, Dict, Optional


class BusinessRulesEngine:
    """
    Simple but effective rules for academic recommendation project
    Easy to implement, explain, and improves user experience
    """
    
    def __init__(self):
        # Rule weights (easy to tune)
        self.SAME_CATEGORY_BOOST = 1.5      # Boost products in same category
        self.PRICE_RANGE_BOOST = 1.3        # Boost products in similar price range
        self.POPULAR_BOOST = 1.2            # Boost popular products
        self.NEW_PRODUCT_BOOST = 1.1        # Boost new products (for diversity)
        self.HIGH_RATING_BOOST = 1.4        # Boost high-rated products
        
        # Thresholds
        self.MIN_RATING = 3.5
        self.PRICE_TOLERANCE = 0.3  # 30% price difference acceptable
        
    def apply_rules(
        self,
        recommendations: List[str],
        all_products: List[Dict],
        context: Optional[Dict] = None
    ) -> List[str]:
        """
        Apply business rules to re-rank recommendations
        
        Args:
            recommendations: List of product IDs from AI model
            all_products: All product data
            context: User context (viewed_product, category_preference, price_range)
        
        Returns:
            Re-ranked list of product IDs
        """
        if not recommendations:
            return []
        
        # Convert to dict for easy lookup
        products_dict = {str(p['_id']): p for p in all_products}
        
        # Calculate scores
        scored_products = []
        
        for product_id in recommendations:
            if product_id not in products_dict:
                continue
            
            product = products_dict[product_id]
            score = 1.0  # Base score
            
            # Rule 1: High rating boost
            rating = product.get('averageRating', 0)
            if rating >= 4.5:
                score *= self.HIGH_RATING_BOOST
            elif rating >= 4.0:
                score *= 1.2
            
            # Rule 2: Popular products (many ratings)
            total_ratings = product.get('totalRatings', 0)
            if total_ratings >= 10:
                score *= self.POPULAR_BOOST
            elif total_ratings >= 5:
                score *= 1.1
            
            # Context-based rules
            if context:
                # Rule 3: Same category as viewed product
                if 'viewed_category' in context:
                    product_category = str(product.get('productCategory', ''))
                    if product_category == context['viewed_category']:
                        score *= self.SAME_CATEGORY_BOOST
                
                # Rule 4: Similar price range
                if 'price_range' in context:
                    product_price = product.get('price', 0)
                    min_price, max_price = context['price_range']
                    if min_price <= product_price <= max_price:
                        score *= self.PRICE_RANGE_BOOST
                
                # Rule 5: User's favorite category
                if 'favorite_categories' in context:
                    product_category = str(product.get('productCategory', ''))
                    if product_category in context['favorite_categories']:
                        score *= 1.3
            
            # Rule 6: Filter out low-rated products (hard rule)
            if rating < self.MIN_RATING and total_ratings >= 3:
                score *= 0.5  # Penalize
            
            scored_products.append((product_id, score))
        
        # Sort by score
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        # Return re-ranked product IDs
        return [pid for pid, score in scored_products]
    
    def diversify_recommendations(
        self,
        recommendations: List[str],
        all_products: List[Dict],
        max_per_category: int = 2
    ) -> List[str]:
        """
        Ensure diversity by limiting products per category
        
        This prevents showing too many similar products
        """
        products_dict = {str(p['_id']): p for p in all_products}
        
        category_count = {}
        diversified = []
        
        for product_id in recommendations:
            if product_id not in products_dict:
                continue
            
            product = products_dict[product_id]
            category = str(product.get('productCategory', 'unknown'))
            
            # Check category limit
            if category_count.get(category, 0) < max_per_category:
                diversified.append(product_id)
                category_count[category] = category_count.get(category, 0) + 1
        
        # If we filtered too many, add back from remaining
        if len(diversified) < len(recommendations) // 2:
            remaining = [p for p in recommendations if p not in diversified]
            diversified.extend(remaining[:len(recommendations) - len(diversified)])
        
        return diversified
    
    def get_user_context(self, user_data: Dict, product_repo) -> Dict:
        """
        Extract user context for rule-based filtering
        
        Args:
            user_data: User's history (orders, ratings, views)
            product_repo: Product repository to get product details
        
        Returns:
            Context dict with user preferences
        """
        context = {}
        
        # Find favorite categories (from orders/ratings)
        category_counts = {}
        
        if 'orders' in user_data:
            for order in user_data['orders']:
                for item in order.get('orderItems', []):
                    product = product_repo.find_by_id(str(item['product']))
                    if product:
                        category = str(product.get('productCategory', ''))
                        category_counts[category] = category_counts.get(category, 0) + 1
        
        if 'ratings' in user_data:
            for rating in user_data['ratings']:
                if rating.get('rating', 0) >= 4:  # Only positive ratings
                    product = product_repo.find_by_id(str(rating['productId']))
                    if product:
                        category = str(product.get('productCategory', ''))
                        category_counts[category] = category_counts.get(category, 0) + 1
        
        # Top 2 favorite categories
        if category_counts:
            sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            context['favorite_categories'] = [cat for cat, _ in sorted_categories[:2]]
        
        # Average price range user buys
        prices = []
        if 'orders' in user_data:
            for order in user_data['orders']:
                for item in order.get('orderItems', []):
                    prices.append(item.get('price', 0))
        
        if prices:
            avg_price = sum(prices) / len(prices)
            tolerance = avg_price * self.PRICE_TOLERANCE
            context['price_range'] = (avg_price - tolerance, avg_price + tolerance)
        
        return context


# Example usage in your hybrid strategy
"""
# In app/services/hybrid.py

from app.business_rules import BusinessRulesEngine

class HybridRecommendationStrategy:
    def __init__(self, ...):
        # ... existing code ...
        self.rules_engine = BusinessRulesEngine()
    
    def recommend(self, user_id: str, n_items: int = 5, context: Optional[Dict] = None):
        # Get AI recommendations (existing code)
        recommendations = self._get_ai_recommendations(user_id, n_items * 2)
        
        # Apply business rules
        all_products = self.product_repo.find_many({}, limit=None)
        
        # Enhance context with user preferences
        user_orders = self.order_repo.get_user_orders(user_id)
        user_ratings = self.rating_repo.get_user_ratings(user_id)
        user_context = self.rules_engine.get_user_context({
            'orders': user_orders,
            'ratings': user_ratings
        }, self.product_repo)
        
        # Merge contexts
        if context:
            user_context.update(context)
        
        # Re-rank with rules
        recommendations = self.rules_engine.apply_rules(
            recommendations,
            all_products,
            user_context
        )
        
        # Diversify
        recommendations = self.rules_engine.diversify_recommendations(
            recommendations,
            all_products,
            max_per_category=2
        )
        
        return recommendations[:n_items]
"""


# Benefits for academic project:
"""
1. ✅ Easy to explain in presentation
   - "We combine AI with business logic"
   - "Rules ensure quality and diversity"
   - Clear, interpretable decisions

2. ✅ Improves metrics immediately
   - Boosts high-quality products
   - Filters low-rated items
   - Better precision without more data

3. ✅ Demonstrates understanding
   - Shows you understand business needs
   - Not just blindly using AI
   - Practical approach

4. ✅ Works with limited data
   - Rules don't need lots of training data
   - Supplements weak AI model
   - Fallback when AI is uncertain

5. ✅ Easy to tune and demo
   - Change weights in real-time
   - Show before/after comparison
   - Explain each rule's impact
"""
