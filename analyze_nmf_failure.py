"""
Phân tích tại sao NMF model không học được gì
- Check interaction matrix sparsity
- Analyze NMF training parameters
- Debug reconstruction error
"""
import pymongo
import numpy as np
import os
from sklearn.decomposition import NMF
import pickle
from pydantic_settings import BaseSettings

# Settings class
class Settings(BaseSettings):
    MONGODB_USERNAME: str
    MONGODB_PASSWORD: str
    MONGODB_DATABASE: str = "test"
    MONGODB_CLUSTER: str = "webbuycake.asd8v.mongodb.net"
    UPSTASH_REDIS_HOST: str = ""
    UPSTASH_REDIS_PORT: int = 6379
    UPSTASH_REDIS_PASSWORD: str = ""
    
    @property
    def mongodb_uri(self) -> str:
        return (
            f"mongodb+srv://{self.MONGODB_USERNAME}:{self.MONGODB_PASSWORD}"
            f"@{self.MONGODB_CLUSTER}/?retryWrites=true&w=majority&appName=WebBuyCake"
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields

# Load settings
settings = Settings()

print(f"🔗 Connecting to MongoDB...")
client = pymongo.MongoClient(settings.mongodb_uri)
db = client[settings.MONGODB_DATABASE]

# Test connection
try:
    client.admin.command('ping')
    print(f"✅ Connected to MongoDB: {settings.MONGODB_DATABASE}\n")
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    exit(1)

print("="*70)
print("🔍 PHÂN TÍCH TẠI SAO NMF KHÔNG HỌC ĐƯỢC GÌ")
print("="*70)

# ============================================================
# [1] ANALYZE INTERACTION MATRIX
# ============================================================
print("\n[1/6] 📊 Analyzing Interaction Matrix")
print("-"*70)

# Get users and products
orders = list(db.orders.find({}))
ratings = list(db.ratings.find({}))

users_from_orders = set(str(order['userId']) for order in orders)
users_from_ratings = set(str(rating['userId']) for rating in ratings)
all_users = sorted(users_from_orders | users_from_ratings)

products_set = set()
for order in orders:
    for item in order.get('orderItems', []):
        products_set.add(str(item['product']))

for rating in ratings:
    if rating.get('productId'):
        products_set.add(str(rating['productId']))

all_products = sorted(products_set)

print(f"   👥 Total users: {len(all_users)}")
print(f"   🛍️  Total products: {len(all_products)}")
print(f"   📦 Total orders: {len(orders)}")
print(f"   ⭐ Total ratings: {len(ratings)}")

# Create mappings
user_to_idx = {uid: idx for idx, uid in enumerate(all_users)}
product_to_idx = {pid: idx for idx, pid in enumerate(all_products)}

# Build interaction matrix
n_users = len(all_users)
n_products = len(all_products)
interactions = np.zeros((n_users, n_products))

print(f"\n   📐 Matrix shape: {n_users} users × {n_products} products = {n_users * n_products:,} cells")

# Add order interactions
for order in orders:
    user_id = str(order.get('userId', ''))
    if user_id not in user_to_idx:
        continue
    user_idx = user_to_idx[user_id]
    
    for item in order.get('orderItems', []):
        product_id = str(item['product'])
        if product_id not in product_to_idx:
            continue
        product_idx = product_to_idx[product_id]
        quantity = item.get('quantity', 1)
        interactions[user_idx, product_idx] += quantity * 2.0

# Add rating interactions
for rating in ratings:
    user_id = str(rating.get('userId', ''))
    product_id = str(rating.get('productId', ''))
    
    if user_id not in user_to_idx or product_id not in product_to_idx:
        continue
    
    user_idx = user_to_idx[user_id]
    product_idx = product_to_idx[product_id]
    rating_value = rating.get('rating', 0)
    interactions[user_idx, product_idx] += rating_value * 0.6

# Normalize to 0-5 scale
max_val = interactions.max()
if max_val > 0:
    interactions = interactions / max_val * 5.0

# Calculate sparsity
non_zero = np.count_nonzero(interactions)
total_cells = n_users * n_products
sparsity = (1 - non_zero / total_cells) * 100

print(f"\n   ✅ Non-zero interactions: {non_zero:,} ({100-sparsity:.2f}%)")
print(f"   ⚠️  Sparsity: {sparsity:.2f}%")
print(f"   📊 Value range: [{interactions.min():.2f}, {interactions.max():.2f}]")
print(f"   📈 Mean value: {interactions.mean():.4f}")
print(f"   📉 Median value: {np.median(interactions):.4f}")

# Check per-user and per-product statistics
user_interactions = np.count_nonzero(interactions, axis=1)
product_interactions = np.count_nonzero(interactions, axis=0)

print(f"\n   👤 Users with 0 interactions: {np.sum(user_interactions == 0)}/{n_users}")
print(f"   👤 Mean interactions per user: {user_interactions.mean():.2f}")
print(f"   👤 Users with ≥5 interactions: {np.sum(user_interactions >= 5)}")

print(f"\n   🛍️  Products with 0 interactions: {np.sum(product_interactions == 0)}/{n_products}")
print(f"   🛍️  Mean interactions per product: {product_interactions.mean():.2f}")
print(f"   🛍️  Products with ≥5 interactions: {np.sum(product_interactions >= 5)}")

# ============================================================
# [2] ANALYZE MATRIX QUALITY
# ============================================================
print("\n[2/6] 🔬 Analyzing Matrix Quality")
print("-"*70)

# Check for zero rows/columns
zero_users = np.sum(user_interactions == 0)
zero_products = np.sum(product_interactions == 0)

print(f"   ⚠️  Zero rows (users): {zero_users}/{n_users} ({zero_users/n_users*100:.1f}%)")
print(f"   ⚠️  Zero columns (products): {zero_products}/{n_products} ({zero_products/n_products*100:.1f}%)")

if zero_users > 0 or zero_products > 0:
    print(f"\n   ❌ PROBLEM: Matrix có rows/columns toàn 0!")
    print(f"      → NMF sẽ học features = 0 cho những users/products này")
    print(f"      → Predictions cho users/products này = 0.0000")

# Check matrix rank
matrix_rank = np.linalg.matrix_rank(interactions)
print(f"\n   📊 Matrix rank: {matrix_rank}")
print(f"   📊 Max possible rank: {min(n_users, n_products)}")

if matrix_rank < 5:
    print(f"   ⚠️  WARNING: Matrix rank quá thấp!")
    print(f"      → Không đủ information để learn meaningful patterns")

# ============================================================
# [3] TEST NMF WITH DIFFERENT PARAMETERS
# ============================================================
print("\n[3/6] 🧪 Testing NMF with Different Parameters")
print("-"*70)

# Test 1: Current parameters (n_components=8)
print("\n   🔧 Test 1: n_components=8 (current)")
try:
    model1 = NMF(n_components=8, init='nndsvd', random_state=42, max_iter=500, tol=1e-3)
    user_features1 = model1.fit_transform(interactions)
    product_features1 = model1.components_
    
    print(f"      Iterations: {model1.n_iter_}")
    print(f"      Reconstruction error: {model1.reconstruction_err_:.6f}")
    print(f"      User features non-zero: {np.count_nonzero(user_features1)}/{user_features1.size} ({np.count_nonzero(user_features1)/user_features1.size*100:.2f}%)")
    print(f"      Product features non-zero: {np.count_nonzero(product_features1)}/{product_features1.size} ({np.count_nonzero(product_features1)/product_features1.size*100:.2f}%)")
    
    # Test prediction
    reconstructed = user_features1 @ product_features1
    prediction_range = [reconstructed.min(), reconstructed.max()]
    print(f"      Prediction range: [{prediction_range[0]:.4f}, {prediction_range[1]:.4f}]")
    
except Exception as e:
    print(f"      ❌ Error: {e}")

# Test 2: Smaller components
print("\n   🔧 Test 2: n_components=3 (smaller)")
try:
    model2 = NMF(n_components=3, init='nndsvd', random_state=42, max_iter=500, tol=1e-3)
    user_features2 = model2.fit_transform(interactions)
    product_features2 = model2.components_
    
    print(f"      Iterations: {model2.n_iter_}")
    print(f"      Reconstruction error: {model2.reconstruction_err_:.6f}")
    print(f"      User features non-zero: {np.count_nonzero(user_features2)}/{user_features2.size} ({np.count_nonzero(user_features2)/user_features2.size*100:.2f}%)")
    print(f"      Product features non-zero: {np.count_nonzero(product_features2)}/{product_features2.size} ({np.count_nonzero(product_features2)/product_features2.size*100:.2f}%)")
    
    reconstructed = user_features2 @ product_features2
    prediction_range = [reconstructed.min(), reconstructed.max()]
    print(f"      Prediction range: [{prediction_range[0]:.4f}, {prediction_range[1]:.4f}]")
    
except Exception as e:
    print(f"      ❌ Error: {e}")

# Test 3: Random init (thay vì nndsvd)
print("\n   🔧 Test 3: n_components=8, init='random'")
try:
    model3 = NMF(n_components=8, init='random', random_state=42, max_iter=500, tol=1e-3)
    user_features3 = model3.fit_transform(interactions)
    product_features3 = model3.components_
    
    print(f"      Iterations: {model3.n_iter_}")
    print(f"      Reconstruction error: {model3.reconstruction_err_:.6f}")
    print(f"      User features non-zero: {np.count_nonzero(user_features3)}/{user_features3.size} ({np.count_nonzero(user_features3)/user_features3.size*100:.2f}%)")
    print(f"      Product features non-zero: {np.count_nonzero(product_features3)}/{product_features3.size} ({np.count_nonzero(product_features3)/product_features3.size*100:.2f}%)")
    
    reconstructed = user_features3 @ product_features3
    prediction_range = [reconstructed.min(), reconstructed.max()]
    print(f"      Prediction range: [{prediction_range[0]:.4f}, {prediction_range[1]:.4f}]")
    
except Exception as e:
    print(f"      ❌ Error: {e}")

# ============================================================
# [4] ANALYZE CURRENT MODEL.PKL
# ============================================================
print("\n[4/6] 📦 Analyzing Current model.pkl")
print("-"*70)

try:
    with open('model.pkl', 'rb') as f:
        data = pickle.load(f)
        saved_user_features = data['user_features']
        saved_product_features = data['product_features']
        
        print(f"   📊 Saved model shape:")
        print(f"      User features: {saved_user_features.shape}")
        print(f"      Product features: {saved_product_features.shape}")
        
        print(f"\n   📊 Feature statistics:")
        print(f"      User features non-zero: {np.count_nonzero(saved_user_features)}/{saved_user_features.size} ({np.count_nonzero(saved_user_features)/saved_user_features.size*100:.2f}%)")
        print(f"      Product features non-zero: {np.count_nonzero(saved_product_features)}/{saved_product_features.size} ({np.count_nonzero(saved_product_features)/saved_product_features.size*100:.2f}%)")
        
        print(f"\n   📊 Value ranges:")
        print(f"      User features: [{saved_user_features.min():.6f}, {saved_user_features.max():.6f}]")
        print(f"      Product features: [{saved_product_features.min():.6f}, {saved_product_features.max():.6f}]")
        
        # Check how many users/products have all-zero features
        zero_user_features = np.sum(np.all(saved_user_features == 0, axis=1))
        zero_product_features = np.sum(np.all(saved_product_features == 0, axis=0))
        
        print(f"\n   ⚠️  Users with all-zero features: {zero_user_features}/{saved_user_features.shape[0]}")
        print(f"   ⚠️  Products with all-zero features: {zero_product_features}/{saved_product_features.shape[1]}")
        
except FileNotFoundError:
    print("   ❌ model.pkl not found")
except Exception as e:
    print(f"   ❌ Error: {e}")

# ============================================================
# [5] ROOT CAUSE ANALYSIS
# ============================================================
print("\n[5/6] 🎯 Root Cause Analysis")
print("-"*70)

issues = []

if sparsity > 99:
    issues.append("❌ Matrix TOO SPARSE (>99%): Không đủ data để learn patterns")

if zero_users > n_users * 0.1:
    issues.append(f"❌ Too many users with zero interactions ({zero_users}/{n_users})")

if zero_products > n_products * 0.1:
    issues.append(f"❌ Too many products with zero interactions ({zero_products}/{n_products})")

if matrix_rank < 5:
    issues.append(f"❌ Matrix rank too low ({matrix_rank}): Not enough information diversity")

if non_zero < 100:
    issues.append(f"❌ Too few interactions ({non_zero}): Need at least 100-200 interactions")

if len(issues) == 0:
    print("   ✅ No obvious issues found in data quality")
else:
    print("   🔍 Identified Issues:")
    for issue in issues:
        print(f"      {issue}")

# ============================================================
# [6] RECOMMENDATIONS
# ============================================================
print("\n[6/6] 💡 Recommendations")
print("-"*70)

print("\n   📝 SOLUTIONS:")
print("   1. 🎲 Remove users/products với zero interactions TRƯỚC KHI train")
print("      → Loại bỏ noise, improve matrix quality")
print()
print("   2. 📊 Add synthetic ratings cho popular products")
print("      → Giúp cold-start users có initial preferences")
print()
print("   3. 🔧 Giảm n_components xuống 3-5 (thay vì 8)")
print("      → Easier to learn with sparse data")
print()
print("   4. 🎯 Try different algorithm: ALS (Alternating Least Squares)")
print("      → Better với sparse matrices, explicit handling of zeros")
print()
print("   5. 🚫 HOẶC: Tạm thời tắt CF, chỉ dùng Simple Rules + Content-Based")
print("      → Simple Rules đã working, CF đang làm predictions worse")

print("\n" + "="*70)
print("✅ ANALYSIS COMPLETE")
print("="*70)
