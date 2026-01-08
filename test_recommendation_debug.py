"""
Debug script to check if CF and Content-Based are actually working
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from pymongo import MongoClient
from dotenv import load_dotenv
from app.core.config import get_settings
from app.repositories import (
    ProductRepository, OrderRepository, RatingRepository, 
    SearchHistoryRepository, ModelMetadataRepository
)
from app.services.collaborative_filtering import CollaborativeFilteringStrategy
from app.services.content_based import ContentBasedFilteringStrategy
from app.services.hybrid import HybridRecommendationStrategy

load_dotenv()

settings = get_settings()

# Connect to MongoDB
username = os.getenv('MONGODB_USERNAME')
password = os.getenv('MONGODB_PASSWORD')
uri = f'mongodb+srv://{username}:{password}@webbuycake.asd8v.mongodb.net/?retryWrites=true&w=majority'
client = MongoClient(uri)
db = client['test']

print("\n" + "="*70)
print("🔍 DEBUGGING RECOMMENDATION SYSTEM")
print("="*70)

# Initialize repositories
product_repo = ProductRepository(db)
order_repo = OrderRepository(db)
rating_repo = RatingRepository(db)
search_repo = SearchHistoryRepository(db)
metadata_repo = ModelMetadataRepository(db)

# Get a random product to test
test_product = db.products.find_one()
test_product_id = str(test_product['_id'])
test_product_name = test_product.get('name', 'Unknown')
test_product_category = test_product.get('productCategory')

print(f"\n📦 Test Product:")
print(f"   ID: {test_product_id}")
print(f"   Name: {test_product_name}")
print(f"   Category: {test_product_category}")

# Get a user who has orders
user_with_orders = db.orders.find_one()
test_user_id = str(user_with_orders['userId']) if user_with_orders else None

print(f"\n👤 Test User: {test_user_id}")

print("\n" + "="*70)
print("🤖 TESTING COLLABORATIVE FILTERING")
print("="*70)

cf_strategy = CollaborativeFilteringStrategy(
    order_repo, rating_repo, product_repo, search_repo, metadata_repo, settings
)

print(f"\nCF Ready: {cf_strategy.is_ready()}")

if cf_strategy.is_ready() and test_user_id:
    print(f"\nCalling CF.recommend(user_id={test_user_id}, n_items=10)...")
    cf_recs = cf_strategy.recommend(test_user_id, n_items=10, context={'current_product_id': test_product_id})
    print(f"CF returned: {len(cf_recs)} recommendations")
    
    if cf_recs:
        print(f"\nCF Recommendations (with categories):")
        for i, pid in enumerate(cf_recs[:5], 1):
            p = db.products.find_one({'_id': pid})
            if p:
                cat = db.categories.find_one({'_id': p.get('productCategory')})
                cat_name = cat.get('categoryName') if cat else 'Unknown'
                print(f"   {i}. {p.get('name', 'Unknown')[:30]:30s} | Category: {cat_name}")
    else:
        print("   ❌ CF returned NO recommendations!")
else:
    print("   ❌ CF not ready or no test user!")

print("\n" + "="*70)
print("🎨 TESTING CONTENT-BASED FILTERING")
print("="*70)

content_strategy = ContentBasedFilteringStrategy(
    product_repo, search_repo, settings
)

print(f"\nContent-Based Ready: {content_strategy.is_ready()}")

if content_strategy.is_ready():
    print(f"\nCalling Content.recommend(user_id={test_user_id}, n_items=10, context with current_product)...")
    content_recs = content_strategy.recommend(test_user_id, n_items=10, context={'current_product_id': test_product_id})
    print(f"Content-Based returned: {len(content_recs)} recommendations")
    
    if content_recs:
        print(f"\nContent-Based Recommendations (with categories):")
        for i, pid in enumerate(content_recs[:5], 1):
            p = db.products.find_one({'_id': pid})
            if p:
                cat = db.categories.find_one({'_id': p.get('productCategory')})
                cat_name = cat.get('categoryName') if cat else 'Unknown'
                same_cat = "✓ SAME" if p.get('productCategory') == test_product_category else "✗ DIFFERENT"
                print(f"   {i}. {p.get('name', 'Unknown')[:30]:30s} | {cat_name:15s} | {same_cat}")
    else:
        print("   ❌ Content-Based returned NO recommendations!")

print("\n" + "="*70)
print("🔀 TESTING HYBRID")
print("="*70)

hybrid_strategy = HybridRecommendationStrategy(
    cf_strategy, content_strategy, product_repo, settings
)

print(f"\nHybrid Ready: {hybrid_strategy.is_ready()}")
print(f"CF Weight: {hybrid_strategy.cf_weight}, Content Weight: {hybrid_strategy.content_weight}")

if hybrid_strategy.is_ready():
    print(f"\nCalling Hybrid.recommend(user_id={test_user_id}, n_items=5)...")
    hybrid_recs = hybrid_strategy.recommend(test_user_id, n_items=5, context={'current_product_id': test_product_id})
    print(f"Hybrid returned: {len(hybrid_recs)} recommendations")
    
    if hybrid_recs:
        print(f"\n🎯 HYBRID Recommendations (FINAL RESULT):")
        categories_used = set()
        for i, pid in enumerate(hybrid_recs, 1):
            from bson import ObjectId
            try:
                p = db.products.find_one({'_id': ObjectId(pid)})
            except:
                p = db.products.find_one({'_id': pid})
            
            if p:
                try:
                    cat = db.categories.find_one({'_id': ObjectId(p.get('productCategory'))})
                except:
                    cat = db.categories.find_one({'_id': p.get('productCategory')})
                cat_name = cat.get('categoryName') if cat else 'Unknown'
                same_cat = "❌ SAME" if p.get('productCategory') == test_product_category else "✅ DIFFERENT"
                categories_used.add(cat_name)
                print(f"   {i}. {p.get('name', 'Unknown')[:30]:30s} | {cat_name:15s} | {same_cat}")
        
        print(f"\n📊 DIVERSITY CHECK:")
        print(f"   Total unique categories: {len(categories_used)}")
        print(f"   Categories: {', '.join(categories_used)}")
        
        same_category_count = 0
        for pid in hybrid_recs:
            try:
                p = db.products.find_one({'_id': ObjectId(pid)})
            except:
                p = db.products.find_one({'_id': pid})
            if p and p.get('productCategory') == test_product_category:
                same_category_count += 1
        print(f"   Same category as test product: {same_category_count}/{len(hybrid_recs)}")
        
        if same_category_count >= 4:
            print(f"\n   ❌ PROBLEM: Too many from same category!")
        elif same_category_count <= 2:
            print(f"\n   ✅ GOOD: Diverse recommendations!")
        else:
            print(f"\n   ⚠️  OK: Moderate diversity")

print("\n" + "="*70)
