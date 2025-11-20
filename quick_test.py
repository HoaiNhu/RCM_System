"""Quick test script"""
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Health check
print("\n=== HEALTH CHECK ===")
r = requests.get(f"{BASE_URL}/health")
print(json.dumps(r.json(), indent=2))

# 2. Model status
print("\n=== MODEL STATUS ===")
r = requests.get(f"{BASE_URL}/status")
status = r.json()
print(json.dumps(status, indent=2))

# 3. Test recommendation
print("\n=== TEST RECOMMENDATION ===")
r = requests.post(
    f"{BASE_URL}/recommend",
    json={"user_id": "6756e4441df899603742e267", "n_items": 5}
)
print(json.dumps(r.json(), indent=2))

# 4. Evaluate model
print("\n=== MODEL ACCURACY ===")
r = requests.get(f"{BASE_URL}/model/evaluate")
metrics = r.json()
print(json.dumps(metrics, indent=2))
print(f"\n📊 Precision: {metrics['precision']*100:.2f}%")
print(f"📊 Recall: {metrics['recall']*100:.2f}%")
print(f"📊 F1 Score: {metrics['f1_score']*100:.2f}%")

if metrics['f1_score'] >= 0.3:
    print("\n✅ Model accuracy is GOOD!")
elif metrics['f1_score'] >= 0.15:
    print("\n⚠ Model accuracy is FAIR")
else:
    print("\n⚠ Model needs more data")
