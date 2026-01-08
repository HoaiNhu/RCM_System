"""
Quick fix script - Make recommendations more diverse by reducing thresholds
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.core.config import get_settings

print("="*70)
print("🔧 QUICK FIX: Improving Recommendation Diversity")
print("="*70)

settings = get_settings()

print(f"\n📋 Current Settings:")
print(f"   MIN_RATING_THRESHOLD: {settings.MIN_RATING_THRESHOLD}")
print(f"   SCORE_THRESHOLD: {settings.SCORE_THRESHOLD}")
print(f"   MIN_TOTAL_RATINGS: {settings.MIN_TOTAL_RATINGS}")

print(f"\n✅ Changes Applied in Code:")
print(f"   1. Lowered MIN_RATING_THRESHOLD: 3.0 → 2.5")
print(f"   2. Lowered SCORE_THRESHOLD: 0.2 → 0.1")
print(f"   3. Lowered MIN_TOTAL_RATINGS: 2 → 1")
print(f"   4. Content-Based: Mix similar + diverse from other categories")
print(f"   5. Fallback: Round-robin selection from different categories")
print(f"   6. Diversity: Max 1 product per category (strict)")

print(f"\n🚀 Next Steps:")
print(f"   1. Restart server: python run.py")
print(f"   2. Test recommendations on any product")
print(f"   3. Check terminal logs for diversity info:")
print(f"      🎨 Diverse: X products from Y categories")
print(f"      🎯 Diversity: Max 1 items per category")
print(f"      ✅ Diversity: Returned 5 items from 4-5 categories")

print("\n" + "="*70)
