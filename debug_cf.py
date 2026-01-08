"""
Debug Collaborative Filtering - Tìm nguyên nhân CF không hoạt động
"""
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import pickle
import numpy as np

load_dotenv()

# Connect MongoDB
username = os.getenv('MONGODB_USERNAME')
password = os.getenv('MONGODB_PASSWORD')
uri = f'mongodb+srv://{username}:{password}@webbuycake.asd8v.mongodb.net/?retryWrites=true&w=majority'
client = MongoClient(uri)
db = client['test']

print('\n' + '='*70)
print('🔍 COLLABORATIVE FILTERING DEBUG')
print('='*70)

# 1. Check if model exists
print('\n[1/6] 📂 Checking model file...')
if os.path.exists('model.pkl'):
    file_size = os.path.getsize('model.pkl') / 1024
    print(f'   ✅ model.pkl exists ({file_size:.1f} KB)')
    
    # Load model
    with open('model.pkl', 'rb') as f:
        data = pickle.load(f)
    
    print(f'\n[2/6] 📊 Model contents:')
    print(f'   Keys: {list(data.keys())}')
    print(f'   Users in model: {len(data.get("user_to_idx", {}))}')
    print(f'   Products in model: {len(data.get("product_to_idx", {}))}')
    
    # Check user features
    if 'user_features' in data:
        user_features = data['user_features']
        print(f'   User features shape: {user_features.shape}')
        print(f'   User features non-zero: {np.count_nonzero(user_features)}/{user_features.size}')
    
    # Check product features
    if 'product_features' in data:
        product_features = data['product_features']
        print(f'   Product features shape: {product_features.shape}')
        print(f'   Product features non-zero: {np.count_nonzero(product_features)}/{product_features.size}')
    
else:
    print('   ❌ model.pkl NOT FOUND!')
    print('   Need to train model first: POST http://localhost:8004/model/train')

# 2. Check database users
print(f'\n[3/6] 👥 Checking users in database...')
users = list(db.users.find().limit(5))
print(f'   Total users in DB: {db.users.count_documents({})}')
if users:
    print(f'   Sample user ID: {users[0]["_id"]}')
    
    # Check if user has orders
    user_id = str(users[0]['_id'])
    user_orders = db.orders.count_documents({'userId': users[0]['_id']})
    user_ratings = db.ratings.count_documents({'userId': users[0]['_id']})
    print(f'   Sample user orders: {user_orders}')
    print(f'   Sample user ratings: {user_ratings}')
    
    # Check if user in model
    if os.path.exists('model.pkl'):
        user_to_idx = data.get('user_to_idx', {})
        if user_id in user_to_idx:
            print(f'   ✅ User EXISTS in model')
            user_idx = user_to_idx[user_id]
            print(f'   User index in model: {user_idx}')
        else:
            print(f'   ❌ User NOT in model')
            print(f'   User IDs in model (first 3): {list(user_to_idx.keys())[:3]}')

# 3. Check products
print(f'\n[4/6] 🍰 Checking products...')
products = list(db.products.find().limit(5))
print(f'   Total products in DB: {db.products.count_documents({})}')
if products:
    print(f'   Sample product ID: {products[0]["_id"]}')
    
    # Check if product in model
    if os.path.exists('model.pkl'):
        product_to_idx = data.get('product_to_idx', {})
        product_id = str(products[0]['_id'])
        if product_id in product_to_idx:
            print(f'   ✅ Product EXISTS in model')
        else:
            print(f'   ❌ Product NOT in model')
            print(f'   Product IDs in model (first 3): {list(product_to_idx.keys())[:3]}')

# 4. Test prediction
print(f'\n[5/6] 🎯 Testing CF prediction...')
if os.path.exists('model.pkl') and users:
    try:
        user_id = str(users[0]['_id'])
        user_to_idx = data.get('user_to_idx', {})
        product_to_idx = data.get('product_to_idx', {})
        
        if user_id in user_to_idx:
            user_idx = user_to_idx[user_id]
            user_vec = data['user_features'][user_idx]
            product_mat = data['product_features']
            
            # Predict scores
            scores = np.dot(user_vec, product_mat)
            
            print(f'   User vector shape: {user_vec.shape}')
            print(f'   Product matrix shape: {product_mat.shape}')
            print(f'   Scores shape: {scores.shape}')
            print(f'   Scores range: [{scores.min():.4f}, {scores.max():.4f}]')
            print(f'   Non-zero scores: {np.count_nonzero(scores)}/{len(scores)}')
            
            # Top products
            top_indices = np.argsort(-scores)[:5]
            print(f'\n   Top 5 predicted products:')
            idx_to_product = {idx: pid for pid, idx in product_to_idx.items()}
            for i, idx in enumerate(top_indices):
                product_id = idx_to_product.get(idx, 'Unknown')
                score = scores[idx]
                print(f'      {i+1}. Product {product_id[:12]}... (score: {score:.4f})')
        else:
            print(f'   ❌ Cannot test: User not in model')
    except Exception as e:
        print(f'   ❌ Error during prediction: {e}')
        import traceback
        traceback.print_exc()

# 5. Check why CF returns 0
print(f'\n[6/6] 🔍 Analyzing why CF returns 0 recommendations...')

if os.path.exists('model.pkl'):
    print('\n   Possible reasons:')
    
    # Check 1: User not in model
    total_users = db.users.count_documents({})
    model_users = len(data.get('user_to_idx', {}))
    if model_users < total_users:
        print(f'   ⚠️  Model has {model_users} users but DB has {total_users}')
        print(f'      → Solution: Retrain model to include new users')
    
    # Check 2: Thresholds too high
    from app.core.config import get_settings
    settings = get_settings()
    print(f'\n   Current thresholds:')
    print(f'      MIN_RATING_THRESHOLD: {settings.MIN_RATING_THRESHOLD}')
    print(f'      SCORE_THRESHOLD: {settings.SCORE_THRESHOLD}')
    print(f'      MIN_TOTAL_RATINGS: {settings.MIN_TOTAL_RATINGS}')
    
    # Check 3: Quality filters too strict
    products_meeting_criteria = 0
    for p_id in data.get('product_to_idx', {}).keys():
        product = db.products.find_one({'_id': p_id})
        if product:
            avg_rating = product.get('averageRating', 0)
            total_ratings = product.get('totalRatings', 0)
            if avg_rating >= settings.MIN_RATING_THRESHOLD and total_ratings >= settings.MIN_TOTAL_RATINGS:
                products_meeting_criteria += 1
    
    print(f'\n   Products passing quality filters: {products_meeting_criteria}/{model_users}')
    if products_meeting_criteria < 5:
        print(f'   ⚠️  Too few products pass quality filters!')
        print(f'      → Solution: Lower MIN_RATING_THRESHOLD or MIN_TOTAL_RATINGS')

print('\n' + '='*70)
print('💡 RECOMMENDATIONS:')
print('='*70)
print('1. If model outdated: POST http://localhost:8004/model/train')
print('2. If thresholds too high: Lower in app/core/config.py')
print('3. If still failing: Use Simple Rules (category-based) as fallback')
print('='*70 + '\n')
