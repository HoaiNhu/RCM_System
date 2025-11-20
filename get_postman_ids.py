"""
Get sample IDs from database for Postman testing
Run this to get real user_ids, product_ids, and category_ids from your database
"""
import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def get_sample_ids():
    """Get sample IDs from MongoDB"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/test")
        client = MongoClient(mongo_uri)
        db = client.get_database()
        
        print("\n" + "="*60)
        print("📋 SAMPLE IDs FOR POSTMAN TESTING")
        print("="*60 + "\n")
        
        # Get users
        print("👥 USER IDs:")
        users = list(db.users.find().limit(5))
        if users:
            for i, user in enumerate(users, 1):
                user_id = str(user['_id'])
                name = user.get('fullname', user.get('username', 'N/A'))
                print(f"   user_id_{i}: {user_id}  ({name})")
        else:
            print("   ⚠️  No users found in database")
        
        # Get products
        print("\n📦 PRODUCT IDs:")
        products = list(db.products.find().limit(5))
        if products:
            for i, product in enumerate(products, 1):
                product_id = str(product['_id'])
                name = product.get('productName', 'N/A')
                print(f"   product_id_{i}: {product_id}  ({name})")
        else:
            print("   ⚠️  No products found in database")
        
        # Get categories
        print("\n🏷️  CATEGORY IDs:")
        categories = list(db.categories.find().limit(5))
        if categories:
            for i, category in enumerate(categories, 1):
                category_id = str(category['_id'])
                name = category.get('categoryName', 'N/A')
                print(f"   category_id_{i}: {category_id}  ({name})")
        else:
            print("   ⚠️  No categories found in database")
        
        # Data statistics
        print("\n" + "="*60)
        print("📊 DATABASE STATISTICS")
        print("="*60)
        print(f"   Users: {db.users.count_documents({})}")
        print(f"   Products: {db.products.count_documents({})}")
        print(f"   Categories: {db.categories.count_documents({})}")
        print(f"   Orders: {db.orders.count_documents({})}")
        print(f"   Ratings: {db.ratings.count_documents({})}")
        
        # Generate JSON for Postman environment
        print("\n" + "="*60)
        print("📝 COPY THIS TO POSTMAN ENVIRONMENT")
        print("="*60 + "\n")
        
        env_json = {
            "base_url": "http://localhost:8000"
        }
        
        if users:
            for i, user in enumerate(users[:3], 1):
                env_json[f"user_id_{i}"] = str(user['_id'])
        
        if products:
            for i, product in enumerate(products[:3], 1):
                env_json[f"product_id_{i}"] = str(product['_id'])
        
        if categories:
            for i, category in enumerate(categories[:2], 1):
                env_json[f"category_id_{i}"] = str(category['_id'])
        
        import json
        print(json.dumps(env_json, indent=2))
        
        print("\n" + "="*60)
        print("✅ Copy the JSON above to your Postman environment!")
        print("="*60 + "\n")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    get_sample_ids()
