from pydantic import BaseModel
from typing import Optional

class RecommendationRequest(BaseModel):
    user_id: str
    product_id: Optional[str] = None

class PopularRequest(BaseModel):
    category: Optional[str] = None

class QuizRecommendationRequest(BaseModel):
    user_id: str
    session_id: str