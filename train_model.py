"""
Quick script to train CF model
Run this after starting the server
"""
import requests
import time

def train_model():
    """Train the collaborative filtering model"""
    print("\n" + "="*60)
    print("🔨 TRAINING COLLABORATIVE FILTERING MODEL")
    print("="*60 + "\n")
    
    try:
        print("📡 Sending training request to server...")
        print("   URL: http://localhost:8000/model/train")
        print("\n⏳ Training in progress...")
        print("   (This may take 1-2 minutes, check server terminal for progress)\n")
        
        response = requests.post("http://localhost:8000/model/train", timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            print("\n" + "✅"*30)
            print("  TRAINING COMPLETED SUCCESSFULLY!")
            print("✅"*30 + "\n")
            print("📊 Result:")
            print(f"   Status: {result.get('status', 'N/A')}")
            print(f"   Message: {result.get('message', 'N/A')}")
            if 'metrics' in result:
                print(f"\n   Metrics:")
                for key, value in result['metrics'].items():
                    print(f"   • {key}: {value}")
        else:
            print(f"\n❌ Training failed with status code: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to server!")
        print("\n💡 Solution:")
        print("   1. Make sure server is running: python run.py")
        print("   2. Check if server is on port 8000")
        print("   3. Try: http://localhost:8000/health")
        
    except requests.exceptions.Timeout:
        print("\n⚠️  Request timeout!")
        print("   Training is still running on server, check terminal logs.")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    print("\n🚀 RCM System - Model Training Script")
    
    # Check if server is running
    try:
        health = requests.get("http://localhost:8000/health", timeout=5)
        if health.status_code == 200:
            print("✓ Server is running\n")
            train_model()
        else:
            print("⚠️  Server responded but not healthy")
    except:
        print("\n❌ Server is not running!")
        print("\n💡 Please start the server first:")
        print("   python run.py")
        print("\nThen run this script again:")
        print("   python train_model.py")
