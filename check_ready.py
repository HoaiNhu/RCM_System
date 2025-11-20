"""Check if server is ready"""
import requests
import time

print("⏳ Waiting for server to be ready...")

for i in range(30):  # Wait up to 30 seconds
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Server is ready!")
            print(f"   Status: {data['status']}")
            print(f"   Model: {data['model']}")
            break
    except:
        pass
    
    print(f"   Waiting... {i+1}s")
    time.sleep(1)
else:
    print("\n⚠ Server took too long to start")
