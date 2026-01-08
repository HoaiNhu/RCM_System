"""
Script to compare metrics before and after improvements
"""
import json
import os

def load_metrics(filename):
    """Load metrics from JSON file"""
    if not os.path.exists(filename):
        return None
    
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def display_comparison():
    """Display metrics comparison"""
    before = load_metrics('metrics_before.json')
    after = load_metrics('metrics_after.json')
    
    print("\n" + "="*80)
    print("📊 METRICS COMPARISON - RCM SYSTEM IMPROVEMENTS")
    print("="*80)
    
    if not before:
        print("⚠️  No 'metrics_before.json' found. Please save current metrics first:")
        print("   POST http://localhost:8000/model/evaluate")
        print("   Save the result to metrics_before.json")
        return
    
    if not after:
        print("⚠️  No 'metrics_after.json' found. Please train and evaluate the improved model:")
        print("   1. POST http://localhost:8000/model/train")
        print("   2. POST http://localhost:8000/model/evaluate")
        print("   3. Save the result to metrics_after.json")
        return
    
    # Display results
    print("\n📈 BEFORE IMPROVEMENTS:")
    print(f"   Precision: {before.get('precision', 0):.4f}")
    print(f"   Recall:    {before.get('recall', 0):.4f}")
    print(f"   F1 Score:  {before.get('f1', 0):.4f}")
    
    print("\n🎯 AFTER IMPROVEMENTS:")
    print(f"   Precision: {after.get('precision', 0):.4f}")
    print(f"   Recall:    {after.get('recall', 0):.4f}")
    print(f"   F1 Score:  {after.get('f1', 0):.4f}")
    
    # Calculate improvements
    print("\n🚀 IMPROVEMENTS:")
    precision_change = (after.get('precision', 0) - before.get('precision', 0)) * 100
    recall_change = (after.get('recall', 0) - before.get('recall', 0)) * 100
    f1_change = (after.get('f1', 0) - before.get('f1', 0)) * 100
    
    print(f"   Precision: {precision_change:+.2f}% (absolute)")
    print(f"   Recall:    {recall_change:+.2f}% (absolute)")
    print(f"   F1 Score:  {f1_change:+.2f}% (absolute)")
    
    # Analysis
    print("\n💡 ANALYSIS:")
    if precision_change > 5:
        print("   ✅ Precision improved significantly - fewer irrelevant recommendations")
    elif precision_change > 0:
        print("   ✓ Precision improved slightly")
    else:
        print("   ⚠️  Precision decreased - may need further tuning")
    
    if recall_change > 5:
        print("   ✅ Recall improved significantly - finding more relevant items")
    elif recall_change < -5:
        print("   ⚠️  Recall decreased - may be filtering too aggressively")
    else:
        print("   ✓ Recall remained stable")
    
    if f1_change > 5:
        print("   ✅ Overall F1 score improved significantly")
    elif f1_change > 0:
        print("   ✓ Overall F1 score improved")
    else:
        print("   ⚠️  F1 score decreased - check balance between precision and recall")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    display_comparison()
