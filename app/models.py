from pydantic import BaseModel
from typing import Optional

class RecommendationRequest(BaseModel):
    user_id: str
    product_id: Optional[str] = None

class PopularRequest(BaseModel):
    category: Optional[str] = None