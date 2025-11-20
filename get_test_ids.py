"""
Script để lấy user IDs và product IDs để test
"""
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = f"mongodb+srv://{os.getenv('MONGODB_USERNAME')}:{os.getenv('MONGODB_PASSWORD')}@webbuycake.asd8v.mongodb.net/?retryWrites=true&w=majority&appName=WebBuyCake"
DB_NAME = os.getenv('MONGODB_DATABASE', 'test')

client = pymongo.MongoClient(MONGODB_URI)
db = client[DB_NAME]

print("\n🔍 Test IDs for Postman:\n")

# Lấy users có orders
print("📌 Users with orders:")
users_with_orders = db.orders.distinct('userId')
for i, user_id in enumerate(users_with_orders[:5], 1):
    print(f"   {i}. {user_id}")

# Lấy top products
print("\n📌 Top Products:")
top_products = list(db.products.find().sort([('averageRating', -1)]).limit(5))
for i, product in enumerate(top_products, 1):
    print(f"   {i}. {product['_id']} - {product.get('name', 'N/A')}")

# Lấy categories
print("\n📌 Categories:")
categories = db.products.distinct('productCategory')
for i, cat in enumerate(categories[:5], 1):
    print(f"   {i}. {cat}")

print("\n")
