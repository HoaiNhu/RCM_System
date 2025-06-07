from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .recommender import recommend, train_or_update_model, evaluate_model, precompute_recommendations
from .utils import connect_to_mongo, connect_to_redis
from .models import RecommendationRequest, PopularRequest
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Recommendation System API")

# Kết nối MongoDB và Redis
db = connect_to_mongo()
redis_client = connect_to_redis()

# Khởi tạo mô hình
try:
    model, dataset = train_or_update_model(db)
    precompute_recommendations(db, model, dataset)
except Exception as e:
    print(f"Lỗi khi khởi tạo mô hình: {e}")

@app.get("/")
async def root():
    return {"message": "Welcome to the Recommendation API!"}

@app.get("/health")
async def health_check():
    try:
        db.command("ping")
        if redis_client:
            redis_client.ping()
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/recommend")
async def get_recommendations(request: RecommendationRequest):
    recommendations = recommend(request.user_id, request.product_id, db, model, dataset, redis_client)
    if not recommendations:
        raise HTTPException(status_code=404, detail="No recommendations found")
    return {"recommendations": recommendations}

@app.post("/recommend/popular")
async def get_popular_products(request: PopularRequest):
    query = {'productCategory': request.category} if request.category else {}
    popular_products = list(db.products.find(query)
                            .sort([('averageRating', -1), ('totalRatings', -1)])
                            .limit(5))
    recommendations = [str(p['_id']) for p in popular_products]
    if not recommendations:
        raise HTTPException(status_code=404, detail="No popular products found")
    return {"recommendations": recommendations}

@app.get("/evaluate-model")
async def get_model_evaluation():
    precision, recall, f1 = evaluate_model(db, model, dataset)
    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1
    }

@app.post("/update-model")
async def update_model():
    last_update = db.model_metadata.find_one({'type': 'last_update'})
    last_timestamp = last_update['timestamp'] if last_update else None
    global model, dataset
    model, dataset = train_or_update_model(db, last_timestamp=last_timestamp)
    precompute_recommendations(db, model, dataset)
    return {"status": "Model updated successfully"}

@app.post("/interaction/log")
async def log_interaction(interaction: dict):
    try:
        db.user_interactions.insert_one(interaction)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log interaction: {str(e)}")