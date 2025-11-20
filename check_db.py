"""
Script để check database collections và dữ liệu
"""
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = f"mongodb+srv://{os.getenv('MONGODB_USERNAME')}:{os.getenv('MONGODB_PASSWORD')}@webbuycake.asd8v.mongodb.net/?retryWrites=true&w=majority&appName=WebBuyCake"
DB_NAME = os.getenv('MONGODB_DATABASE', 'test')

client = pymongo.MongoClient(MONGODB_URI)
db = client[DB_NAME]

print(f"\n🔍 Checking database: {DB_NAME}\n")

# List all collections
collections = db.list_collection_names()
print(f"📋 Collections: {collections}\n")

# Count documents in each collection
for collection_name in collections:
    count = db[collection_name].count_documents({})
    print(f"   {collection_name}: {count} documents")

# Check specific collections
print("\n📊 Checking recommendation-related collections:\n")

if 'orders' in collections:
    orders_count = db.orders.count_documents({})
    print(f"   ✅ orders: {orders_count}")
    if orders_count > 0:
        sample_order = db.orders.find_one()
        print(f"      Sample order keys: {list(sample_order.keys())}")
else:
    print("   ❌ No 'orders' collection")

if 'ratings' in collections:
    ratings_count = db.ratings.count_documents({})
    print(f"   ✅ ratings: {ratings_count}")
    if ratings_count > 0:
        sample_rating = db.ratings.find_one()
        print(f"      Sample rating keys: {list(sample_rating.keys())}")
else:
    print("   ❌ No 'ratings' collection")

if 'products' in collections:
    products_count = db.products.count_documents({})
    print(f"   ✅ products: {products_count}")
else:
    print("   ❌ No 'products' collection")

if 'users' in collections:
    users_count = db.users.count_documents({})
    print(f"   ✅ users: {users_count}")
else:
    print("   ❌ No 'users' collection")

print("\n")
