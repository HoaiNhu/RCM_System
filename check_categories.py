from pymongo import MongoClient
import os
from dotenv import load_dotenv
from collections import Counter
from bson import ObjectId

load_dotenv()

username = os.getenv('MONGODB_USERNAME')
password = os.getenv('MONGODB_PASSWORD')
uri = f'mongodb+srv://{username}:{password}@webbuycake.asd8v.mongodb.net/?retryWrites=true&w=majority'

client = MongoClient(uri)
db = client['test']

print('\n' + '='*70)
print('📊 CATEGORIES DISTRIBUTION IN PRODUCTS')
print('='*70)

# Get all products
products = list(db.products.find())
print(f'\nTotal products: {len(products)}')

# Extract categories
cat_counts = Counter()
cat_names = {}

for p in products:
    cat = p.get('productCategory')
    if cat:
        if isinstance(cat, dict):
            cat_id = str(cat.get('_id', ''))
        else:
            cat_id = str(cat)
        
        cat_counts[cat_id] += 1
        
        # Get category name
        if cat_id and cat_id not in cat_names:
            try:
                cat_doc = db.categories.find_one({'_id': ObjectId(cat_id)})
                if cat_doc:
                    cat_names[cat_id] = cat_doc.get('categoryName', 'Unknown')
                else:
                    cat_names[cat_id] = 'Unknown'
            except:
                cat_names[cat_id] = 'Unknown'

print(f'Total categories: {len(cat_counts)}\n')

print('Products per category:')
print('-'*70)
for cat_id, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
    cat_name = cat_names.get(cat_id, 'Unknown')
    percentage = (count / len(products)) * 100
    print(f'  {cat_name[:30]:30s} | {count:3d} products ({percentage:5.1f}%)')

print('\n' + '='*70)
print('🎯 DIVERSITY CHECK')
print('='*70)

# Check if distribution is balanced
max_count = max(cat_counts.values())
min_count = min(cat_counts.values())
avg_count = sum(cat_counts.values()) / len(cat_counts)

print(f'\nMax products in one category: {max_count}')
print(f'Min products in one category: {min_count}')
print(f'Average products per category: {avg_count:.1f}')

if max_count > avg_count * 2:
    print('\n⚠️  WARNING: Imbalanced distribution!')
    print(f'   Some categories have {max_count} products while others have {min_count}')
    print('   This may cause recommendation bias.')
else:
    print('\n✅ Distribution is relatively balanced')

print('\n' + '='*70)
