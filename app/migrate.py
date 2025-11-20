"""
Migration script to backup old code and activate new architecture
"""
import os
import shutil
from datetime import datetime

# Paths
APP_DIR = os.path.dirname(__file__)
BACKUP_DIR = os.path.join(APP_DIR, 'backup_old_code')

# Files to backup
OLD_FILES = [
    'main.py',
    'recommender.py',
    'models.py',
    'utils.py'
]

def backup_old_code():
    """Backup old code to backup folder"""
    print("Backing up old code...")
    
    # Create backup directory with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{BACKUP_DIR}_{timestamp}"
    os.makedirs(backup_path, exist_ok=True)
    
    # Backup each file
    for filename in OLD_FILES:
        src = os.path.join(APP_DIR, filename)
        if os.path.exists(src):
            dst = os.path.join(backup_path, filename)
            shutil.copy2(src, dst)
            print(f"  ✓ Backed up: {filename}")
    
    print(f"\n✓ Old code backed up to: {backup_path}\n")
    return backup_path


def activate_new_code():
    """Rename main_new.py to main.py"""
    print("Activating new code...")
    
    new_main = os.path.join(APP_DIR, 'main_new.py')
    old_main = os.path.join(APP_DIR, 'main.py')
    
    if os.path.exists(new_main):
        # Backup old main.py if exists
        if os.path.exists(old_main):
            backup_main = os.path.join(APP_DIR, 'main_backup.py')
            shutil.move(old_main, backup_main)
            print(f"  ✓ Moved old main.py to main_backup.py")
        
        # Activate new main
        shutil.move(new_main, old_main)
        print(f"  ✓ Activated new main.py")
    
    print("\n✓ New architecture activated!\n")


def print_summary():
    """Print summary of changes"""
    print("="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    print("\n📁 New Architecture Structure:")
    print("""
app/
├── core/
│   ├── config.py           # Settings & configuration
│   └── dependencies.py     # Dependency injection
├── repositories/
│   ├── base.py            # Base repository pattern
│   └── repositories.py    # Concrete repositories
├── services/
│   ├── base.py            # Strategy interfaces
│   ├── collaborative_filtering.py  # CF with NMF
│   ├── content_based.py   # Content-Based with TF-IDF
│   ├── hybrid.py          # Hybrid strategy
│   └── additional_services.py      # Quiz & Popular
├── api/
│   └── v1/
│       ├── health.py      # Health endpoints
│       ├── recommendations.py  # Recommendation endpoints
│       ├── model.py       # Model management
│       └── debug.py       # Debug endpoints
├── schemas/
│   └── __init__.py        # Pydantic schemas
└── main.py                # FastAPI application
    """)
    
    print("\n✨ Key Improvements:")
    print("  1. ✓ Clean architecture with separation of concerns")
    print("  2. ✓ SOLID principles applied throughout")
    print("  3. ✓ Hybrid recommendations (CF + Content-Based)")
    print("  4. ✓ Search history integration for better accuracy")
    print("  5. ✓ Modular routes with dependency injection")
    print("  6. ✓ Repository pattern for data access")
    print("  7. ✓ Strategy pattern for recommendation algorithms")
    
    print("\n📝 Next Steps:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Test locally: uvicorn app.main:app --reload")
    print("  3. Check health: http://localhost:8000/health")
    print("  4. View docs: http://localhost:8000/docs")
    print("  5. Test recommendations with Postman collection")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("RCM SYSTEM - CODE MIGRATION")
    print("="*60 + "\n")
    
    # Backup old code
    backup_path = backup_old_code()
    
    # Activate new code
    activate_new_code()
    
    # Print summary
    print_summary()
    
    print("\n✅ Migration complete!\n")
