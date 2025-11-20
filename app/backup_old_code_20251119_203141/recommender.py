"""
Recommendation System sử dụng scikit-learn NMF (Non-negative Matrix Factorization)
Thay thế lightfm với công nghệ mới và ổn định hơn
"""
from bson import ObjectId
import numpy as np
import os
from datetime import datetime
from sklearn.decomposition import NMF
import pickle
import json
from .utils import analyze_comment


def prepare_data(db, last_timestamp=None):
    """
    Chuẩn bị dữ liệu cho NMF recommendation system.
    Tạo user-item interaction matrix từ orders và ratings.
    """
    try:
        print("Bắt đầu prepare_data với NMF...")
        
        # Query filter cho dữ liệu mới
        query = {'createdAt': {'$gt': last_timestamp}} if last_timestamp else {}
        
        # Lấy tất cả users và products
        users_from_orders = set(str(order['userId']) for order in db.orders.find(query) if order.get('userId'))
        users_from_ratings = set(str(rating['userId']) for rating in db.ratings.find(query) if rating.get('userId'))
        all_users = sorted(users_from_orders | users_from_ratings)
        
        products_from_orders = set(str(item['product']) for order in db.orders.find(query) 
                                   for item in order.get('orderItems', []))
        products_from_ratings = set(str(rating['productId']) for rating in db.ratings.find(query) 
                                   if rating.get('productId'))
        all_products = sorted(products_from_ratings | products_from_orders)
        
        print(f"Users: {len(all_users)}, Products: {len(all_products)}")
        
        if not all_users or not all_products:
            print("Không có dữ liệu đủ để tạo model")
            return None, None, None, None
        
        # Tạo mapping từ ID sang index
        user_to_idx = {user_id: idx for idx, user_id in enumerate(all_users)}
        product_to_idx = {product_id: idx for idx, product_id in enumerate(all_products)}
        
        # Tạo interaction matrix (user x product)
        n_users = len(all_users)
        n_products = len(all_products)
        interactions = np.zeros((n_users, n_products))
        
        # Thêm interactions từ orders
        print("Đang xử lý orders...")
        for order in db.orders.find(query):
            if not order.get('userId'):
                continue
            user_id = str(order['userId'])
            if user_id not in user_to_idx:
                continue
            user_idx = user_to_idx[user_id]
            
            for item in order.get('orderItems', []):
                product_id = str(item['product'])
                if product_id not in product_to_idx:
                    continue
                product_idx = product_to_idx[product_id]
                quantity = item.get('quantity', 1)
                interactions[user_idx, product_idx] += quantity * 2.0  # Weight cho purchase
        
        # Thêm interactions từ ratings
        print("Đang xử lý ratings...")
        for rating in db.ratings.find(query):
            if not rating.get('userId') or not rating.get('productId'):
                continue
            user_id = str(rating['userId'])
            product_id = str(rating['productId'])
            
            if user_id not in user_to_idx or product_id not in product_to_idx:
                continue
            
            user_idx = user_to_idx[user_id]
            product_idx = product_to_idx[product_id]
            
            rating_value = rating.get('rating', 0)
            comment = rating.get('comment', '')
            comment_score = analyze_comment(comment)
            
            # Kết hợp rating và comment score
            weight = rating_value * 0.6 + comment_score * 0.4
            interactions[user_idx, product_idx] += max(weight, 0)
        
        # Normalize interactions (tránh giá trị quá lớn)
        max_val = interactions.max()
        if max_val > 0:
            interactions = interactions / max_val * 5.0  # Scale về 0-5
        
        print(f"Interaction matrix shape: {interactions.shape}")
        print(f"Non-zero interactions: {np.count_nonzero(interactions)}")
        
        return interactions, user_to_idx, product_to_idx, all_products
        
    except Exception as e:
        print(f"Lỗi trong prepare_data: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e


def train_or_update_model(db, model_path='model.pkl', mappings_path='mappings.pkl', last_timestamp=None):
    """
    Train hoặc update NMF model cho recommendation.
    """
    try:
        print("Bắt đầu train_or_update_model với NMF...")
        
        # Chuẩn bị dữ liệu
        interactions, user_to_idx, product_to_idx, all_products = prepare_data(db, last_timestamp)
        
        if interactions is None:
            print("Không thể tạo model do thiếu dữ liệu")
            # Load model cũ nếu có
            if os.path.exists(model_path) and os.path.exists(mappings_path):
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                with open(mappings_path, 'rb') as f:
                    mappings = pickle.load(f)
                return model, mappings
            return None, None
        
        # Tạo NMF model
        print("Training NMF model...")
        n_components = min(20, min(interactions.shape) - 1)  # Số latent factors
        
        model = NMF(
            n_components=n_components,
            init='nndsvd',  # Better initialization than random
            random_state=42,
            max_iter=500,
            alpha_W=0.01,  # L2 regularization
            alpha_H=0.01,
            l1_ratio=0.5,  # Mix of L1 and L2
            verbose=1
        )
        
        # Fit model
        W = model.fit_transform(interactions)  # User features
        H = model.components_  # Product features
        
        print(f"Model trained: W shape {W.shape}, H shape {H.shape}")
        print(f"Reconstruction error: {model.reconstruction_err_:.4f}")
        
        # Lưu model và mappings
        mappings = {
            'user_to_idx': user_to_idx,
            'product_to_idx': product_to_idx,
            'all_products': all_products,
            'W': W  # User features để predict nhanh hơn
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        with open(mappings_path, 'wb') as f:
            pickle.dump(mappings, f)
        
        # Cập nhật metadata
        db.model_metadata.update_one(
            {'type': 'last_update'},
            {'$set': {'timestamp': datetime.utcnow()}},
            upsert=True
        )
        
        print("train_or_update_model hoàn thành")
        return model, mappings
        
    except Exception as e:
        print(f"Lỗi trong train_or_update_model: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e


def evaluate_model(db, model, mappings, k=5):
    """
    Đánh giá model với precision, recall, F1.
    """
    try:
        user_to_idx = mappings['user_to_idx']
        product_to_idx = mappings['product_to_idx']
        
        # Lấy test set từ orders gần nhất
        orders = list(db.orders.find().sort('createdAt', -1))
        test_size = max(1, int(0.1 * len(orders)))
        test_orders = orders[:test_size]
        
        precisions = []
        recalls = []
        
        for order in test_orders:
            user_id = str(order['userId']) if order.get('userId') else None
            if not user_id or user_id not in user_to_idx:
                continue
            
            actual_items = [str(item['product']) for item in order.get('orderItems', [])]
            recommended = recommend(user_id, None, db, model, mappings, None, k)
            
            relevant = set(actual_items) & set(recommended)
            precision = len(relevant) / len(recommended) if recommended else 0
            recall = len(relevant) / len(actual_items) if actual_items else 0
            
            precisions.append(precision)
            recalls.append(recall)
        
        avg_precision = np.mean(precisions) if precisions else 0
        avg_recall = np.mean(recalls) if recalls else 0
        f1_score = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0
        
        return avg_precision, avg_recall, f1_score
        
    except Exception as e:
        print(f"Lỗi trong evaluate_model: {str(e)}")
        return 0, 0, 0


def recommend(user_id, current_product_id, db, model, mappings, redis_client, n_items=5):
    """
    Recommend products cho user sử dụng NMF model.
    """
    try:
        user_to_idx = mappings['user_to_idx']
        product_to_idx = mappings['product_to_idx']
        all_products = mappings['all_products']
        W = mappings['W']
        
        # Check cache
        cache_key = f"rec:{user_id}:{current_product_id or 'None'}"
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        
        # Nếu user mới (không có trong training set)
        if user_id not in user_to_idx:
            return get_fallback_recommendations(user_id, current_product_id, db, n_items, redis_client, cache_key)
        
        # Lấy user features và predict scores
        user_idx = user_to_idx[user_id]
        user_features = W[user_idx]
        product_features = model.components_  # H matrix
        
        # Calculate scores: user_features @ product_features.T
        scores = user_features @ product_features
        
        # Lấy top products
        top_indices = np.argsort(-scores)
        
        recommendations = []
        for idx in top_indices:
            if len(recommendations) >= n_items:
                break
            
            product_id = all_products[idx]
            
            # Skip current product
            if current_product_id and product_id == current_product_id:
                continue
            
            try:
                product = db.products.find_one({'_id': ObjectId(product_id)})
                if product:
                    avg_rating = product.get('averageRating', 0)
                    # Filter low quality products
                    if avg_rating >= 2.0:
                        recommendations.append(product_id)
            except:
                continue
        
        # Fallback nếu không đủ
        if len(recommendations) < n_items:
            fallback = get_fallback_recommendations(user_id, current_product_id, db, n_items - len(recommendations), None, None)
            recommendations.extend([p for p in fallback if p not in recommendations])
        
        recommendations = recommendations[:n_items]
        
        # Cache result
        if redis_client:
            redis_client.setex(cache_key, 3600, json.dumps(recommendations))
        
        return recommendations
        
    except Exception as e:
        print(f"Lỗi trong recommend: {str(e)}")
        return get_fallback_recommendations(user_id, current_product_id, db, n_items, redis_client, None)


def get_fallback_recommendations(user_id, current_product_id, db, n_items, redis_client, cache_key):
    """
    Fallback recommendations khi không thể dùng model.
    """
    try:
        # Nếu có current_product, recommend similar products
        if current_product_id:
            product = db.products.find_one({'_id': ObjectId(current_product_id)})
            if product and 'productCategory' in product:
                category = product['productCategory']
                similar_products = list(db.products.find({'productCategory': category})
                                       .sort([('averageRating', -1), ('totalRatings', -1)])
                                       .limit(n_items + 5))
                recommendations = [str(p['_id']) for p in similar_products 
                                 if str(p['_id']) != current_product_id][:n_items]
                
                if recommendations:
                    if redis_client and cache_key:
                        redis_client.setex(cache_key, 3600, json.dumps(recommendations))
                    return recommendations
        
        # Fallback to popular products
        popular_products = list(db.products.find()
                               .sort([('averageRating', -1), ('totalRatings', -1)])
                               .limit(n_items))
        recommendations = [str(p['_id']) for p in popular_products]
        
        if redis_client and cache_key:
            redis_client.setex(cache_key, 3600, json.dumps(recommendations))
        
        return recommendations
        
    except Exception as e:
        print(f"Lỗi trong get_fallback_recommendations: {str(e)}")
        return []


def recommend_from_quiz(user_id, session_id, db, redis_client, n_items=20):
    """
    Recommend products dựa trên quiz responses.
    """
    cache_key = f"quiz_rec:{user_id}:{session_id}"
    
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    
    # Fetch quiz responses
    responses = list(db.quiz_responses.find({'userId': user_id, 'sessionId': session_id, 'completed': True}))
    if not responses:
        return get_fallback_recommendations(user_id, None, db, n_items, redis_client, cache_key)
    
    # Mapping keywords
    mood_to_keywords = {
        'happy': ['vui', 'sáng', 'ngọt', 'tươi', 'màu sắc'],
        'sad': ['êm dịu', 'trầm', 'chocolate', 'dịu ngọt', 'ấm áp'],
        'stressed': ['nhẹ nhàng', 'thư giãn', 'trà', 'tinh tế', 'bình yên'],
        'custom': []
    }
    memory_to_keywords = {
        'milk': ['sữa', 'kem', 'dịu', 'trẻ thơ', 'mềm mại'],
        'vanilla': ['vani', 'ngọt nhẹ', 'tinh tế', 'cổ điển', 'thơm'],
        'chocolate': ['chocolate', 'đậm đà', 'ngọt đắng', 'giàu', 'ấm'],
        'custom': []
    }
    
    # Collect keywords
    keywords = []
    for response in responses:
        quiz = db.quizzes.find_one({'_id': ObjectId(response['quizId'])})
        if not quiz:
            continue
        answer = response['answer']
        custom_answer = response.get('customAnswer')
        
        if quiz['type'] == 'mood':
            keywords.extend(mood_to_keywords.get(answer, []))
            if answer == 'custom' and custom_answer:
                keywords.append(custom_answer.lower())
        elif quiz['type'] == 'memory':
            keywords.extend(memory_to_keywords.get(answer, []))
            if answer == 'custom' and custom_answer:
                keywords.append(custom_answer.lower())
    
    keywords = [k for k in set(keywords) if k]
    if not keywords:
        return get_fallback_recommendations(user_id, None, db, n_items, redis_client, cache_key)
    
    # Search products
    query = {
        '$or': [
            {'name': {'$regex': k, '$options': 'i'}} for k in keywords
        ] + [
            {'description': {'$regex': k, '$options': 'i'}} for k in keywords
        ]
    }
    products = list(db.products.find(query)
                   .sort([('averageRating', -1), ('totalRatings', -1)])
                   .limit(n_items))
    
    recommendations = [str(p['_id']) for p in products if p.get('averageRating', 0) >= 2.0]
    
    # Fallback if needed
    if len(recommendations) < n_items:
        popular = list(db.products.find()
                      .sort([('averageRating', -1), ('totalRatings', -1)])
                      .limit(n_items - len(recommendations)))
        recommendations.extend([str(p['_id']) for p in popular if str(p['_id']) not in recommendations])
    
    recommendations = recommendations[:n_items]
    
    if redis_client:
        redis_client.setex(cache_key, 3600, json.dumps(recommendations))
    
    return recommendations


def precompute_recommendations(db, model, mappings):
    """
    Precompute recommendations cho một số users để cache.
    """
    try:
        if db is None or model is None or mappings is None:
            print("Không thể precompute do thiếu model hoặc database")
            return
        
        user_to_idx = mappings['user_to_idx']
        print(f"Precomputing recommendations cho {len(user_to_idx)} users...")
        
        # Giới hạn số users để tránh timeout
        max_users = 100
        users_to_compute = list(user_to_idx.keys())[:max_users]
        
        success_count = 0
        for i, user_id in enumerate(users_to_compute):
            try:
                if i % 20 == 0:
                    print(f"Progress: {i}/{len(users_to_compute)}")
                
                recommended = recommend(user_id, None, db, model, mappings, None)
                if recommended:
                    db.recommendations.update_one(
                        {'userId': user_id},
                        {'$set': {'recommended': recommended, 'updatedAt': datetime.utcnow()}},
                        upsert=True
                    )
                    success_count += 1
            except Exception as e:
                print(f"Lỗi precompute cho user {user_id}: {e}")
                continue
        
        print(f"Precompute hoàn thành: {success_count}/{len(users_to_compute)} users")
        
    except Exception as e:
        print(f"Lỗi trong precompute_recommendations: {str(e)}")
        import traceback
        traceback.print_exc()
