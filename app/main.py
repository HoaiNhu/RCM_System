"""
Main FastAPI application
Refactored with clean architecture following SOLID principles
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading
import time

from .api import api_router
from .core.dependencies import get_recommendation_service


# Application metadata
APP_TITLE = "RCM System - Hybrid Recommendation Engine"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = """
Hybrid Recommendation System combining:
- **Collaborative Filtering** (NMF matrix factorization)
- **Content-Based Filtering** (TF-IDF + cosine similarity)
- **Search History Integration** for improved accuracy

Built with clean architecture following SOLID principles.
"""

# Create FastAPI application
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Global state for model training
model_loading = False


def initialize_model_background():
    """Initialize model in background thread"""
    global model_loading
    
    try:
        model_loading = True
        import time
        start_time = time.time()
        
        print("\n" + "🚀"*30)
        print("  STARTING BACKGROUND MODEL INITIALIZATION")
        print("🚀"*30 + "\n")
        
        # Get recommendation service (triggers lazy loading)
        print("⏳ Initializing services...")
        service = get_recommendation_service()
        
        # Train if not already trained
        if not service.is_ready():
            print("\n📚 Model not found, training from scratch...")
            service.train(force_retrain=False)
        else:
            print("\n✅ Model loaded from disk (fast startup)")
        
        elapsed = time.time() - start_time
        print("\n" + "✅"*30)
        print(f"  INITIALIZATION COMPLETE in {elapsed:.2f}s")
        print("✅"*30)
        print("\n" + "="*60)
        print("🎉 SERVER IS READY TO ACCEPT REQUESTS!")
        print("📍 API Documentation: http://localhost:8004/docs")
        print("🔍 Health Check: http://localhost:8004/health")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error in background initialization: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠️  Server started but model initialization failed!")
        print("   You can still use the API with fallback recommendations.\n")
    finally:
        model_loading = False


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    print(f"\n{'='*60}")
    print(f"{APP_TITLE} v{APP_VERSION}")
    print(f"{'='*60}\n")
    
    # Start model initialization in background thread
    thread = threading.Thread(target=initialize_model_background, daemon=True)
    thread.start()
    
    print("✓ Application started successfully")
    print("✓ Model loading in background...\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    print("\n" + "="*60)
    print("Shutting down application...")
    print("="*60 + "\n")


if __name__ == "__main__":
    import uvicorn
    import os
    import sys
    
    # Add project root to Python path for direct execution
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8004,
        reload=True
    )
