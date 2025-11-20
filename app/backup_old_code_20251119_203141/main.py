from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from .recommender import recommend, train_or_update_model, evaluate_model, precompute_recommendations, recommend_from_quiz
from .utils import connect_to_mongo, connect_to_redis
from .models import RecommendationRequest, PopularRequest, QuizRecommendationRequest
from datetime import datetime
import os
from dotenv import load_dotenv
import asyncio
import threading

load_dotenv()

app = FastAPI(title="Recommendation System API")

# Kết nối MongoDB và Redis
db = connect_to_mongo()
redis_client = connect_to_redis()

# Khởi tạo mô hình NMF - Lazy loading để tránh crash khi startup
model, mappings = None, None
model_loading = False

def initialize_model_background():
    """Khởi tạo model trong background thread - KHÔNG BLOCK startup"""
    global model, mappings, model_loading
    model_loading = True
    try:
        if db is not None:
            print("🔄 Bắt đầu khởi tạo NMF model trong background...")
            model, mappings = train_or_update_model(db)
            if model and mappings:
                print("✅ Khởi tạo mô hình NMF thành công")
                # Precompute trong background
                try:
                    precompute_recommendations(db, model, mappings)
                    print("✅ Precompute recommendations hoàn tất")
                except Exception as e:
                    print(f"⚠️ Precompute warning: {e}")
            else:
                print("⚠️ Không có đủ dữ liệu để train model, sẽ dùng fallback")
        else:
            print("⚠️ Database chưa kết nối")
    except Exception as e:
        print(f"⚠️ Lỗi khi khởi tạo mô hình: {e}")
        import traceback
        traceback.print_exc()
    finally:
        model_loading = False

# Khởi động model training trong background thread (KHÔNG BLOCK app startup)
print("🚀 App đang khởi động... Model sẽ được train trong background")
threading.Thread(target=initialize_model_background, daemon=True).start()

@app.get("/")
async def root():
    if model_loading:
        status = "training"
    elif model and mappings:
        status = "ready"
    else:
        status = "fallback_mode"
    
    return {
        "message": "Welcome to the Recommendation API!",
        "model_status": status,
        "version": "2.0-NMF"
    }

@app.get("/health")
async def health_check():
    try:
        db_status = "connected"
        redis_status = "connected"
        model_status = "ready" if model and mappings else "fallback"
        
        if db is not None:
            db.command("ping")
        else:
            db_status = "disconnected"
            
        if redis_client is not None:
            redis_client.ping()
        else:
            redis_status = "disconnected"
            
        if model_loading:
            model_status = "training"
        
        return {
            "status": "healthy",
            "database": db_status,
            "redis": redis_status,
            "model": model_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/recommend")
async def get_recommendations(request: RecommendationRequest):
    # Nếu model chưa ready, vẫn trả về recommendations (dùng fallback)
    if model is None or mappings is None:
        print("⚠️ Model chưa ready, sử dụng fallback recommendations")
        # Import fallback function
        from .recommender import get_fallback_recommendations
        recommendations = get_fallback_recommendations(
            request.user_id, 
            request.product_id, 
            db, 
            5, 
            redis_client, 
            None
        )
    else:
        recommendations = recommend(request.user_id, request.product_id, db, model, mappings, redis_client)
    
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

@app.post("/recommend/quiz")
async def get_quiz_recommendations(request: QuizRecommendationRequest):
    recommendations = recommend_from_quiz(request.user_id, request.session_id, db, redis_client)
    if not recommendations:
        raise HTTPException(status_code=404, detail="No recommendations found based on quiz responses")
    return {"recommendations": recommendations}

@app.get("/evaluate-model")
async def get_model_evaluation():
    if model is None or mappings is None:
        return {
            "precision": 0,
            "recall": 0,
            "f1_score": 0,
            "status": "Model chưa được train, không thể evaluate"
        }
    precision, recall, f1 = evaluate_model(db, model, mappings)
    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "status": "success"
    }

@app.post("/update-model")
async def update_model():
    try:
        print("Bắt đầu cập nhật mô hình...")
        
        # Kiểm tra kết nối database
        if db is None:
            raise HTTPException(status_code=500, detail="Không thể kết nối database")
        
        # Test kết nối database
        try:
            db.command("ping")
            print("Database connection OK")
        except Exception as db_error:
            print(f"Database connection failed: {db_error}")
            raise HTTPException(status_code=500, detail=f"Lỗi kết nối database: {str(db_error)}")
        
        # Lấy thông tin cập nhật cuối
        last_update = db.model_metadata.find_one({'type': 'last_update'})
        last_timestamp = last_update['timestamp'] if last_update else None
        print(f"Timestamp cập nhật cuối: {last_timestamp}")
        
        # Cập nhật mô hình NMF
        global model, mappings
        print("Đang training/updating NMF model...")
        model, mappings = train_or_update_model(db, last_timestamp=last_timestamp)
        print("Model training hoàn thành")
        
        # Precompute recommendations (với timeout)
        try:
            if model and mappings:
                print("Đang precompute recommendations...")
                precompute_recommendations(db, model, mappings)
                print("Precompute hoàn thành")
        except Exception as precompute_error:
            print(f"Lỗi khi precompute: {precompute_error}")
            # Không raise lỗi, chỉ log và tiếp tục
        
        return {"status": "Model updated successfully"}
    except Exception as e:
        print(f"Lỗi khi cập nhật mô hình: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật mô hình: {str(e)}")

@app.post("/interaction/log")
async def log_interaction(interaction: dict):
    try:
        db.user_interactions.insert_one(interaction)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log interaction: {str(e)}")

@app.get("/debug/data")
async def debug_data():
    try:
        if db is None:
            return {"error": "Database connection failed"}
        
        # Đếm số lượng documents trong các collections
        orders_count = db.orders.count_documents({})
        ratings_count = db.ratings.count_documents({})
        products_count = db.products.count_documents({})
        users_count = db.users.count_documents({})
        
        # Lấy một vài documents mẫu
        sample_order = db.orders.find_one({})
        sample_rating = db.ratings.find_one({})
        
        return {
            "database_info": {
                "orders_count": orders_count,
                "ratings_count": ratings_count,
                "products_count": products_count,
                "users_count": users_count
            },
            "sample_order": sample_order,
            "sample_rating": sample_rating
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/connection")
async def debug_connection():
    try:
        if db is None:
            return {"error": "Database connection failed"}
        
        # Test ping
        ping_result = db.command("ping")
        
        # Lấy danh sách collections
        collections = db.list_collection_names()
        
        return {
            "ping_result": ping_result,
            "collections": collections,
            "database_name": db.name
        }
    except Exception as e:
        return {"error": str(e)}