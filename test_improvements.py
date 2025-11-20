"""
Quick script to test model improvements after implementing changes
"""
import requests
import time
import json

def print_separator():
    print("\n" + "="*70)

def print_metrics(data, label=""):
    """Print metrics in a nice format"""
    if label:
        print(f"\n{label}")
    print(f"   Precision: {data.get('precision', 0):.4f}")
    print(f"   Recall:    {data.get('recall', 0):.4f}")
    print(f"   F1 Score:  {data.get('f1_score', 0):.4f}")

def test_improvements():
    """Test model improvements step by step"""
    print_separator()
    print("🧪 TESTING MODEL IMPROVEMENTS")
    print_separator()
    
    base_url = "http://localhost:8000"
    
    # Check if server is running
    try:
        health = requests.get(f"{base_url}/health", timeout=5)
        if health.status_code != 200:
            print("\n❌ Server is not healthy!")
            return
        print("\n✅ Server is running")
    except:
        print("\n❌ Cannot connect to server!")
        print("\n💡 Start server first: python run.py")
        return
    
    # Step 1: Evaluate current model
    print_separator()
    print("STEP 1: Evaluate Current Model (Before)")
    print_separator()
    
    try:
        print("\n📊 Getting current metrics...")
        response = requests.get(f"{base_url}/model/evaluate", timeout=30)
        
        if response.status_code == 200:
            before_metrics = response.json()
            print_metrics(before_metrics, "📉 Current Metrics:")
            
            # Save for comparison
            with open('metrics_before.json', 'w') as f:
                json.dump(before_metrics, f, indent=2)
            print("\n   Saved to: metrics_before.json")
        else:
            print(f"\n❌ Evaluation failed: {response.status_code}")
            print(f"   {response.text}")
            return
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    # Step 2: Check data statistics
    print_separator()
    print("STEP 2: Check Data Statistics")
    print_separator()
    
    try:
        print("\n📈 Getting database stats...")
        response = requests.get(f"{base_url}/debug/stats", timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            print(f"\n   Total Orders:  {stats.get('total_orders', 0)}")
            print(f"   Total Ratings: {stats.get('total_ratings', 0)}")
            print(f"   Total Users:   {stats.get('total_users', 0)}")
            print(f"   Total Products: {stats.get('total_products', 0)}")
            
            # Calculate data density
            total_interactions = stats.get('total_orders', 0) + stats.get('total_ratings', 0)
            total_users = stats.get('total_users', 1)
            total_products = stats.get('total_products', 1)
            density = (total_interactions / (total_users * total_products)) * 100
            
            print(f"\n   Data Density: {density:.2f}%")
            
            if density < 0.5:
                print("   ⚠️  Very sparse data! Consider generating more synthetic data.")
            elif density < 2:
                print("   ⚠️  Sparse data. Synthetic data recommended.")
            else:
                print("   ✅ Good data density!")
                
        else:
            print(f"\n⚠️  Could not get stats (endpoint may not exist)")
            
    except Exception as e:
        print(f"\n⚠️  Could not get stats: {e}")
    
    # Step 3: Retrain model
    print_separator()
    print("STEP 3: Retrain Model with Improvements")
    print_separator()
    
    print("\n🔨 Training model...")
    print("   (This may take 1-2 minutes)")
    
    try:
        response = requests.post(f"{base_url}/model/train", timeout=300)
        
        if response.status_code == 200:
            train_result = response.json()
            print(f"\n✅ {train_result.get('message', 'Training completed')}")
            
            # Wait a bit for model to be ready
            time.sleep(2)
        else:
            print(f"\n❌ Training failed: {response.status_code}")
            print(f"   {response.text}")
            return
            
    except Exception as e:
        print(f"\n❌ Error training: {e}")
        return
    
    # Step 4: Evaluate after retraining
    print_separator()
    print("STEP 4: Evaluate After Improvements")
    print_separator()
    
    try:
        print("\n📊 Evaluating improved model...")
        response = requests.get(f"{base_url}/model/evaluate", timeout=30)
        
        if response.status_code == 200:
            after_metrics = response.json()
            print_metrics(after_metrics, "📈 New Metrics:")
            
            # Save for comparison
            with open('metrics_after.json', 'w') as f:
                json.dump(after_metrics, f, indent=2)
            print("\n   Saved to: metrics_after.json")
        else:
            print(f"\n❌ Evaluation failed: {response.status_code}")
            return
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    # Step 5: Compare results
    print_separator()
    print("STEP 5: Improvement Analysis")
    print_separator()
    
    print("\n📊 COMPARISON:")
    print("\n   Metric      | Before  | After   | Change")
    print("   " + "-"*50)
    
    for metric in ['precision', 'recall', 'f1_score']:
        before = before_metrics.get(metric, 0)
        after = after_metrics.get(metric, 0)
        change = after - before
        change_pct = (change / before * 100) if before > 0 else 0
        
        # Format metric name
        metric_name = metric.replace('_', ' ').title()[:11]
        
        # Emoji for change
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
        
        print(f"   {metric_name:11} | {before:.4f} | {after:.4f} | {emoji} {change:+.4f} ({change_pct:+.1f}%)")
    
    # Overall assessment
    print_separator()
    print("ASSESSMENT")
    print_separator()
    
    f1_before = before_metrics.get('f1_score', 0)
    f1_after = after_metrics.get('f1_score', 0)
    improvement = f1_after - f1_before
    improvement_pct = (improvement / f1_before * 100) if f1_before > 0 else 0
    
    if improvement > 0.05:
        print("\n✅ EXCELLENT IMPROVEMENT!")
        print(f"   F1 Score improved by {improvement_pct:.1f}%")
    elif improvement > 0.02:
        print("\n✅ Good improvement!")
        print(f"   F1 Score improved by {improvement_pct:.1f}%")
    elif improvement > 0:
        print("\n➖ Minor improvement")
        print(f"   F1 Score improved by {improvement_pct:.1f}%")
    else:
        print("\n⚠️  No improvement or decreased")
        print(f"   F1 Score changed by {improvement_pct:.1f}%")
        print("\n💡 Possible reasons:")
        print("   • Need more training data")
        print("   • Model needs more epochs")
        print("   • Hyperparameters need tuning")
    
    # Recommendations
    print_separator()
    print("RECOMMENDATIONS")
    print_separator()
    
    if f1_after < 0.15:
        print("\n⚠️  F1 Score is still low (<0.15)")
        print("\n💡 Try:")
        print("   1. Generate more synthetic data:")
        print("      python generate_synthetic_data.py")
        print("   2. Increase NMF components in recommender.py")
        print("   3. Check if real data exists in database")
    elif f1_after < 0.25:
        print("\n✅ F1 Score is acceptable (0.15-0.25)")
        print("\n💡 To improve further:")
        print("   1. Add more real user interactions")
        print("   2. Fine-tune quality weights in recommender.py")
        print("   3. Experiment with diversity settings")
    else:
        print("\n✅ F1 Score is good (>0.25)!")
        print("\n💡 Next steps:")
        print("   1. Test recommendations with real users")
        print("   2. Monitor precision/recall trade-off")
        print("   3. Consider A/B testing")
    
    print_separator()
    print("✅ TEST COMPLETE!")
    print_separator()
    print()


if __name__ == "__main__":
    test_improvements()
