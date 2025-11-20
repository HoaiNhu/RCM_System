"""Quick run script for development"""
import uvicorn

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Starting RCM System Server...")
    print("="*60 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
