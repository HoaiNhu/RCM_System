from bson import ObjectId
import numpy as np
import os
from datetime import datetime
from lightfm import LightFM
from lightfm.data import Dataset
import pickle
import json
from .utils import analyze_comment

def prepare_data(db, new_orders_only=False, last_timestamp=None):
    dataset = Dataset()
    query = {'createdAt': {'$gt': last_timestamp}} if new_orders_only and last_timestamp else {}
    
    users_from_orders = set(str(order['userId']) for order in db.orders.find(query) if order.get('userId'))
    users_from_ratings = set(str(rating['userId']) for rating in db.ratings.find(query) if rating.get('userId'))
    users = users_from_orders | users_from_ratings
    
    products_from_orders = set(str(item['product']) for order in db.orders.find(query) for item in order.get('orderItems', []))
    products_from_ratings = set(str(rating['productId']) for rating in db.ratings.find(query) if rating.get('productId'))
    products = products_from_orders | products_from_ratings
    
    if new_orders_only:
        dataset.fit_partial(users=users, items=products)
    else:
        dataset.fit(users=users, items=products)
    
    interactions = []
    for order in db.orders.find(query):
        if order.get('userId'):
            user_id = str(order['userId'])
            for item in order.get('orderItems', []):
                product_id = str(item['product'])
                quantity = item.get('quantity', 1)
                interactions.append((user_id, product_id, quantity))
    
    for rating in db.ratings.find(query):
        if rating.get('userId') and rating.get('productId'):
            user_id = str(rating['userId'])
            product_id = str(rating['productId'])
            rating_value = rating.get('rating', 0)
            comment = rating.get('comment', '')
            comment_score = analyze_comment(comment)
            product = db.products.find_one({'_id': ObjectId(product_id)})
            avg_rating_bonus = product.get('averageRating', 0) * 0.3 if product else 0
            weight = rating_value * 0.5 + comment_score * 0.2 + avg_rating_bonus
            interactions.append((user_id, product_id, max(weight, 0)))
    
    (interactions_matrix, weights) = dataset.build_interactions(interactions)
    return dataset, interactions_matrix

def train_or_update_model(db, model_path='model.pkl', dataset_path='dataset.pkl', last_timestamp=None):
    if os.path.exists(model_path) and os.path.exists(dataset_path):
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        with open(dataset_path, 'rb') as f:
            dataset = pickle.load(f)
        dataset, interactions_matrix = prepare_data(db, new_orders_only=True, last_timestamp=last_timestamp)
        model.fit_partial(interactions_matrix, epochs=20, num_threads=2, verbose=True)
    else:
        dataset, interactions_matrix = prepare_data(db)
        model = LightFM(
            loss='warp',
            random_state=42,
            learning_rate=0.1,  # Tăng learning rate
            no_components=20    # Giảm số components
        )
        model.fit(interactions_matrix, epochs=50, num_threads=2, verbose=True)
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    with open(dataset_path, 'wb') as f:
        pickle.dump(dataset, f)
    db.model_metadata.update_one(
        {'type': 'last_update'},
        {'$set': {'timestamp': datetime.utcnow()}},
        upsert=True
    )
    return model, dataset

def evaluate_model(db, model, dataset, k=5):
    user_ids, item_ids = dataset.mapping()[0], dataset.mapping()[2]
    orders = list(db.orders.find().sort('createdAt', -1))
    test_size = max(1, int(0.1 * len(orders)))
    test_orders = orders[:test_size]
    precisions = []
    recalls = []
    for order in test_orders:
        user_id = str(order['userId']) if order.get('userId') else None
        if user_id not in user_ids:
            continue
        actual_items = [str(item['product']) for item in order.get('orderItems', [])]
        recommended = recommend(user_id, None, db, model, dataset, None, k)
        relevant = set(actual_items) & set(recommended)
        precision = len(relevant) / len(recommended) if recommended else 0
        recall = len(relevant) / len(actual_items) if actual_items else 0
        precisions.append(precision)
        recalls.append(recall)
    avg_precision = np.mean(precisions) if precisions else 0
    avg_recall = np.mean(recalls) if recalls else 0
    f1_score = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0
    return avg_precision, avg_recall, f1_score

def recommend(user_id, current_product_id, db, model, dataset, redis_client, n_items=5):
    user_ids, item_ids = dataset.mapping()[0], dataset.mapping()[2]
    cache_key = f"rec:{user_id}:{current_product_id or 'None'}"
    
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    
    if user_id not in user_ids:
        if current_product_id:
            try:
                product = db.products.find_one({'_id': ObjectId(current_product_id)})
                if product and 'productCategory' in product:
                    category = product['productCategory']
                    similar_products = list(db.products.find({'productCategory': category})
                                            .sort([('averageRating', -1), ('totalRatings', -1)])
                                            .limit(n_items))
                    recommendations = [str(p['_id']) for p in similar_products if str(p['_id']) != current_product_id]
                    if redis_client:
                        redis_client.setex(cache_key, 3600, json.dumps(recommendations))
                    return recommendations
            except:
                pass
        popular_products = list(db.products.find()
                                .sort([('averageRating', -1), ('totalRatings', -1)])
                                .limit(n_items))
        recommendations = [str(p['_id']) for p in popular_products]
        if redis_client:
            redis_client.setex(cache_key, 3600, json.dumps(recommendations))
        return recommendations
    
    user_idx = user_ids[user_id]
    scores = model.predict(user_idx, np.arange(len(item_ids)))
    top_items = np.argsort(-scores)[:n_items + 10]
    recommendations = []
    for i in top_items:
        product_id = list(item_ids.keys())[i]
        if current_product_id and product_id == current_product_id:
            continue
        try:
            product = db.products.find_one({'_id': ObjectId(product_id)})
            if product:
                avg_rating = product.get('averageRating', 0)
                ratings = list(db.ratings.find({'productId': ObjectId(product_id)}))
                comment_score = sum(analyze_comment(r.get('comment', '')) for r in ratings) / (len(ratings) or 1)
                if avg_rating >= 2.0 or comment_score > 0:  # Lọc sản phẩm rating thấp
                    recommendations.append(product_id)
        except:
            continue
        if len(recommendations) >= n_items:
            break
    
    if not recommendations and current_product_id:
        try:
            product = db.products.find_one({'_id': ObjectId(current_product_id)})
            if product and 'productCategory' in product:
                category = product['productCategory']
                similar_products = list(db.products.find({'productCategory': category})
                                        .sort([('averageRating', -1), ('totalRatings', -1)])
                                        .limit(n_items))
                recommendations = [str(p['_id']) for p in similar_products if str(p['_id']) != current_product_id]
        except:
            pass
    
    if not recommendations:
        popular_products = list(db.products.find()
                                .sort([('averageRating', -1), ('totalRatings', -1)])
                                .limit(n_items))
        recommendations = [str(p['_id']) for p in popular_products]
    
    if redis_client:
        redis_client.setex(cache_key, 3600, json.dumps(recommendations))
    return recommendations[:n_items]

def recommend_from_quiz(user_id, session_id, db, redis_client, n_items=20):
    cache_key = f"quiz_rec:{user_id}:{session_id}"
    
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    
    # Fetch quiz responses for the user and session
    responses = list(db.quiz_responses.find({'userId': user_id, 'sessionId': session_id, 'completed': True}))
    if not responses:
        popular_products = list(db.products.find()
                                .sort([('averageRating', -1), ('totalRatings', -1)])
                                .limit(n_items))
        recommendations = [str(p['_id']) for p in popular_products]
        if redis_client:
            redis_client.setex(cache_key, 3600, json.dumps(recommendations))
        return recommendations
    
    # Mapping of quiz answers to product attributes
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
    
    # Collect keywords based on quiz responses
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
    
    # Remove duplicates and empty keywords
    keywords = [k for k in set(keywords) if k]
    if not keywords:
        popular_products = list(db.products.find()
                                .sort([('averageRating', -1), ('totalRatings', -1)])
                                .limit(n_items))
        recommendations = [str(p['_id']) for p in popular_products]
        if redis_client:
            redis_client.setex(cache_key, 3600, json.dumps(recommendations))
        return recommendations
    
    # Search products matching keywords in name or description
    query = {
        '$or': [
            {'name': {'$regex': k, '$options': 'i'}} for k in keywords
        ] + [
            {'description': {'$regex': k, '$options': 'i'}} for k in keywords
        ]
    }
    products = list(db.products.find(query)
                    .sort([('averageRating', -1), ('totalRatings', -1), ('price', 1)])
                    .limit(n_items))
    
    recommendations = []
    for product in products:
        avg_rating = product.get('averageRating', 0)
        if avg_rating >= 2.0:  # Filter low-rated products
            recommendations.append(str(product['_id']))
    
    # Fallback to popular products if insufficient matches
    if len(recommendations) < n_items:
        popular_products = list(db.products.find()
                                .sort([('averageRating', -1), ('totalRatings', -1)])
                                .limit(n_items - len(recommendations)))
        recommendations.extend([str(p['_id']) for p in popular_products if str(p['_id']) not in recommendations])
    
    if redis_client:
        redis_client.setex(cache_key, 3600, json.dumps(recommendations))
    return recommendations[:n_items]

def precompute_recommendations(db, model, dataset):
    user_ids = dataset.mapping()[0]
    for user_id in user_ids:
        recommended = recommend(user_id, None, db, model, dataset, None)
        db.recommendations.update_one(
            {'userId': user_id},
            {'$set': {'recommended': recommended, 'updatedAt': datetime.utcnow()}},
            upsert=True
        )