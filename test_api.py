"""
Script to test API endpoints and evaluate model accuracy
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_health():
    """Test health endpoint"""
    print_section("1. HEALTH CHECK")
    response = requests.get(f"{BASE_URL}/health")
    data = response.json()
    print(json.dumps(data, indent=2))
    return data

def test_status():
    """Test model status"""
    print_section("2. MODEL STATUS")
    response = requests.get(f"{BASE_URL}/status")
    data = response.json()
    print(json.dumps(data, indent=2))
    return data

def test_data_stats():
    """Get data statistics"""
    print_section("3. DATA STATISTICS")
    response = requests.get(f"{BASE_URL}/debug/data")
    data = response.json()
    print(json.dumps(data, indent=2))
    return data

def test_recommendations(user_id):
    """Test hybrid recommendations"""
    print_section(f"4. HYBRID RECOMMENDATIONS for user: {user_id}")
    response = requests.post(
        f"{BASE_URL}/recommend",
        json={"user_id": user_id, "n_items": 5}
    )
    data = response.json()
    print(json.dumps(data, indent=2))
    return data

def test_popular():
    """Test popular products"""
    print_section("5. POPULAR PRODUCTS")
    response = requests.post(
        f"{BASE_URL}/recommend/popular",
        json={"n_items": 5}
    )
    data = response.json()
    print(json.dumps(data, indent=2))
    return data

def test_evaluate_model():
    """Evaluate model accuracy"""
    print_section("6. MODEL EVALUATION (Precision, Recall, F1)")
    response = requests.get(f"{BASE_URL}/model/evaluate")
    data = response.json()
    print(json.dumps(data, indent=2))
    
    # Print metrics in a nice format
    print("\n📊 ACCURACY METRICS:")
    print(f"  • Precision: {data['precision']:.4f} ({data['precision']*100:.2f}%)")
    print(f"  • Recall:    {data['recall']:.4f} ({data['recall']*100:.2f}%)")
    print(f"  • F1 Score:  {data['f1_score']:.4f} ({data['f1_score']*100:.2f}%)")
    
    # Interpret results
    f1 = data['f1_score']
    if f1 >= 0.5:
        print(f"\n✅ EXCELLENT: Model accuracy is very good!")
    elif f1 >= 0.3:
        print(f"\n✓ GOOD: Model accuracy is acceptable")
    elif f1 >= 0.15:
        print(f"\n⚠ FAIR: Model accuracy needs improvement")
    else:
        print(f"\n⚠ POOR: Model needs more data or tuning")
    
    return data

def main():
    print("\n" + "🚀"*30)
    print("  RCM SYSTEM API TEST & MODEL EVALUATION")
    print("🚀"*30)
    
    try:
        # 1. Health check
        health = test_health()
        
        # 2. Model status
        status = test_status()
        
        # 3. Data statistics
        stats = test_data_stats()
        
        # 4. Test recommendations with real user IDs
        test_user_ids = [
            "6756e4441df899603742e267",
            "676eaf5cbf34ce78983409c3",
            "677352004c7e2661dce1596a"
        ]
        
        for user_id in test_user_ids[:1]:  # Test first user
            test_recommendations(user_id)
        
        # 5. Popular products
        test_popular()
        
        # 6. Evaluate model accuracy
        evaluation = test_evaluate_model()
        
        # Summary
        print_section("SUMMARY")
        print(f"✓ Health: {health['status']}")
        print(f"✓ Database: {health['database']}")
        print(f"✓ Model: {status['status']}")
        print(f"✓ Users in model: {status['n_users']}")
        print(f"✓ Products in model: {status['n_products']}")
        print(f"✓ Total documents: {stats['total_documents']}")
        print(f"✓ F1 Score: {evaluation['f1_score']:.4f}")
        
        print("\n✅ All tests completed successfully!\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
