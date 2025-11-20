"""
Additional recommendation services: Quiz-based and Popular products
"""
from typing import List, Dict, Optional
from ..repositories import (
    ProductRepository,
    QuizResponseRepository,
    QuizRepository
)
from ..core.config import Settings


class QuizRecommendationService:
    """Service for quiz-based recommendations"""
    
    # Keyword mappings for quiz responses
    MOOD_KEYWORDS = {
        'happy': ['vui', 'sáng', 'ngọt', 'tươi', 'màu sắc'],
        'sad': ['êm dịu', 'trầm', 'chocolate', 'dịu ngọt', 'ấm áp'],
        'stressed': ['nhẹ nhàng', 'thư giãn', 'trà', 'tinh tế', 'bình yên'],
        'excited': ['phấn khích', 'mạnh mẽ', 'đậm đà', 'nổi bật'],
        'custom': []
    }
    
    MEMORY_KEYWORDS = {
        'milk': ['sữa', 'kem', 'dịu', 'trẻ thơ', 'mềm mại'],
        'vanilla': ['vani', 'ngọt nhẹ', 'tinh tế', 'cổ điển', 'thơm'],
        'chocolate': ['chocolate', 'đậm đà', 'ngọt đắng', 'giàu', 'ấm'],
        'fruit': ['trái cây', 'tươi mát', 'chua ngọt', 'sảng khoái'],
        'custom': []
    }
    
    def __init__(
        self,
        product_repo: ProductRepository,
        quiz_response_repo: QuizResponseRepository,
        quiz_repo: QuizRepository,
        settings: Settings
    ):
        self.product_repo = product_repo
        self.quiz_response_repo = quiz_response_repo
        self.quiz_repo = quiz_repo
        self.settings = settings
    
    def recommend_from_quiz(self, user_id: str, session_id: str, n_items: int = 20) -> List[str]:
        """Generate recommendations based on quiz responses"""
        try:
            # Get quiz responses
            responses = self.quiz_response_repo.get_user_session_responses(user_id, session_id)
            
            if not responses:
                return []
            
            # Extract keywords from responses
            keywords = self._extract_keywords_from_responses(responses)
            
            if not keywords:
                return []
            
            # Search products by keywords
            products = self.product_repo.search_by_keywords(keywords, limit=n_items * 2)
            
            # Filter by quality and return top N
            recommendations = [
                str(p['_id']) for p in products
                if p.get('averageRating', 0) >= self.settings.MIN_RATING_THRESHOLD
            ][:n_items]
            
            return recommendations
            
        except Exception as e:
            print(f"Error in quiz recommendations: {e}")
            return []
    
    def _extract_keywords_from_responses(self, responses: List[Dict]) -> List[str]:
        """Extract keywords from quiz responses"""
        keywords = []
        
        for response in responses:
            quiz_id = response.get('quizId')
            answer = response.get('answer')
            custom_answer = response.get('customAnswer')
            
            # Get quiz details
            quiz = self.quiz_repo.find_by_id(str(quiz_id))
            if not quiz:
                continue
            
            quiz_type = quiz.get('type')
            
            # Map answer to keywords
            if quiz_type == 'mood':
                keywords.extend(self.MOOD_KEYWORDS.get(answer, []))
            elif quiz_type == 'memory':
                keywords.extend(self.MEMORY_KEYWORDS.get(answer, []))
            
            # Add custom answer if provided
            if answer == 'custom' and custom_answer:
                keywords.append(custom_answer.lower())
        
        # Return unique keywords
        return list(set(k for k in keywords if k))


class PopularProductService:
    """Service for popular product recommendations"""
    
    def __init__(
        self,
        product_repo: ProductRepository,
        settings: Settings
    ):
        self.product_repo = product_repo
        self.settings = settings
    
    def get_popular_products(self, category_id: Optional[str] = None, n_items: int = 5) -> List[str]:
        """Get popular products, optionally filtered by category"""
        try:
            if category_id:
                # Get popular products in category
                products = self.product_repo.get_by_category(category_id, limit=n_items)
                
                # If no products in category, try all products
                if not products:
                    print(f"   No products in category {category_id}, trying all products...")
                    products = self.product_repo.get_popular_products(
                        limit=n_items,
                        min_rating=self.settings.MIN_RATING_THRESHOLD
                    )
            else:
                # Get overall popular products
                products = self.product_repo.get_popular_products(
                    limit=n_items,
                    min_rating=self.settings.MIN_RATING_THRESHOLD
                )
                
                # If no products meet rating threshold, get any products
                if not products:
                    print(f"   No products with rating >= {self.settings.MIN_RATING_THRESHOLD}, getting any products...")
                    products = self.product_repo.find_many({}, limit=n_items)
            
            return [str(p['_id']) for p in products]
            
        except Exception as e:
            print(f"Error getting popular products: {e}")
            import traceback
            traceback.print_exc()
            return []
