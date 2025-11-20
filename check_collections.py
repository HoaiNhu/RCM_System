"""
Check MongoDB collections and data for RCM System
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def check_collections():
    """Check all collections and their data counts"""
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            username = os.getenv("MONGODB_USERNAME")
            password = os.getenv("MONGODB_PASSWORD")
            cluster = os.getenv("MONGODB_CLUSTER", "webbuycake.asd8v.mongodb.net")
            database = os.getenv("MONGODB_DATABASE", "test")
            mongo_uri = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority&appName=WebBuyCake"
        
        client = MongoClient(mongo_uri)
        db = client.get_database()
        
        print("\n" + "="*60)
        print("📊 MONGODB COLLECTIONS - DATA CHECK")
        print("="*60 + "\n")
        
        print(f"🔗 Database: {db.name}")
        
        # Collections to check
        collections = {
            'Core Collections (Required)': [
                'users',
                'products',
                'orders',
                'ratings',
                'categories'
            ],
            'Optional Collections': [
                'searchHistory',
                'quiz_responses',
                'quizzes'
            ],
            'System Collections': [
                'model_metadata',
                'recommendations'
            ]
        }
        
        total_data = {}
        
        for category, coll_list in collections.items():
            print(f"\n{category}:")
            print("-" * 60)
            
            for coll_name in coll_list:
                count = db[coll_name].count_documents({})
                total_data[coll_name] = count
                
                # Status indicator
                if coll_name in ['orders', 'ratings']:
                    status = "✅" if count > 0 else "❌ REQUIRED FOR CF MODEL"
                elif coll_name in ['users', 'products']:
                    status = "✅" if count > 0 else "❌ REQUIRED"
                else:
                    status = "✅" if count > 0 else "ℹ️  Optional"
                
                print(f"   {coll_name:20s} {count:6d} documents   {status}")
        
        # CF Model Readiness Check
        print("\n" + "="*60)
        print("🤖 COLLABORATIVE FILTERING MODEL - READINESS CHECK")
        print("="*60 + "\n")
        
        orders_count = total_data.get('orders', 0)
        ratings_count = total_data.get('ratings', 0)
        users_count = total_data.get('users', 0)
        products_count = total_data.get('products', 0)
        
        print(f"   Users:    {users_count}")
        print(f"   Products: {products_count}")
        print(f"   Orders:   {orders_count}")
        print(f"   Ratings:  {ratings_count}")
        print()
        
        # Check if we have enough data
        if orders_count == 0 and ratings_count == 0:
            print("❌ CF MODEL CANNOT BE TRAINED!")
            print("\n💡 Solution:")
            print("   Need at least ONE of:")
            print("   • Orders data (users buying products)")
            print("   • Ratings data (users rating products)")
            print("\n   Recommendations will use:")
            print("   • Content-Based filtering (product similarity)")
            print("   • Popular products (fallback)")
            
        elif orders_count + ratings_count < 10:
            print("⚠️  CF MODEL CAN TRAIN BUT MAY BE WEAK")
            print(f"\n   Current interactions: {orders_count + ratings_count}")
            print("   Recommended: 50+ interactions for good performance")
            print("\n   Current recommendations will use:")
            print("   • Hybrid (CF + Content-Based)")
            print("   • May fall back to popular products")
            
        else:
            print("✅ CF MODEL CAN BE TRAINED!")
            print(f"\n   Total interactions: {orders_count + ratings_count}")
            print("   This is sufficient for training.")
            print("\n   Ready to train:")
            print("   POST http://localhost:8000/model/train")
        
        # Sample data check
        print("\n" + "="*60)
        print("📝 SAMPLE DATA")
        print("="*60 + "\n")
        
        if users_count > 0:
            user = db.users.find_one()
            print(f"Sample User:")
            print(f"   ID: {user['_id']}")
            print(f"   Name: {user.get('fullname', user.get('username', 'N/A'))}")
        
        if products_count > 0:
            product = db.products.find_one()
            print(f"\nSample Product:")
            print(f"   ID: {product['_id']}")
            print(f"   Name: {product.get('productName', 'N/A')}")
        
        if orders_count > 0:
            order = db.orders.find_one()
            print(f"\nSample Order:")
            print(f"   ID: {order['_id']}")
            print(f"   User: {order.get('userId', 'N/A')}")
            print(f"   Items: {len(order.get('orderItems', []))}")
        
        if ratings_count > 0:
            rating = db.ratings.find_one()
            print(f"\nSample Rating:")
            print(f"   ID: {rating['_id']}")
            print(f"   User: {rating.get('userId', 'N/A')}")
            print(f"   Product: {rating.get('productId', 'N/A')}")
            print(f"   Rating: {rating.get('rating', 'N/A')}")
        
        print("\n" + "="*60 + "\n")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_collections()
