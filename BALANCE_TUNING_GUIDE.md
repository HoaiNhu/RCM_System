# ⚖️ Balance Precision-Recall Tuning Guide

## 📊 Current Results

### Before All Changes:

- Precision: **10.6%** ❌
- Recall: **66.0%** ✓
- F1: **18.3%** ❌

### After First Improvements (Too Strict):

- Precision: **52.7%** ✅ (too high)
- Recall: **32.8%** ❌ (too low)
- F1: **40.4%** ✓

### After Balance (Current Config):

- Target Precision: **38-42%**
- Target Recall: **48-55%**
- Target F1: **42-47%**

---

## 🎯 Understanding the Trade-off

### High Precision, Low Recall (Strict Filtering)

```
Precision: 52.7%, Recall: 32.8%
→ Recommendations rất chính xác nhưng miss nhiều sản phẩm tốt
→ Users thấy ít choices, có thể bỏ lỡ sản phẩm họ thích
```

### Balanced (Sweet Spot)

```
Precision: 38-42%, Recall: 48-55%
→ Đa số recommendations đúng, và find được nhiều relevant items
→ Best for user experience và conversion
```

### High Recall, Low Precision (Loose Filtering)

```
Precision: 15-20%, Recall: 65%+
→ Show nhiều sản phẩm nhưng nhiều items không relevant
→ Users phải scroll nhiều, experience kém
```

---

## 🔧 Tuning Parameters

### Level 1: Core Thresholds (config.py)

#### SCORE_THRESHOLD

```python
# Precision quá cao, Recall thấp → Giảm
SCORE_THRESHOLD: float = 0.15  # Giảm từ 0.2

# Precision thấp, Recall quá cao → Tăng
SCORE_THRESHOLD: float = 0.25  # Tăng từ 0.2

# Current
SCORE_THRESHOLD: float = 0.2  # Balanced
```

#### MIN_RATING_THRESHOLD

```python
# Precision quá cao → Giảm (accept sản phẩm rating thấp hơn)
MIN_RATING_THRESHOLD: float = 2.5  # Giảm từ 3.0

# Precision thấp → Tăng (chỉ high-quality products)
MIN_RATING_THRESHOLD: float = 3.5  # Tăng từ 3.0

# Current
MIN_RATING_THRESHOLD: float = 3.0  # Balanced
```

#### MIN_TOTAL_RATINGS

```python
# Recall thấp → Giảm (accept products với ít reviews)
MIN_TOTAL_RATINGS: int = 1  # Giảm từ 2

# Precision thấp → Tăng (chỉ products được review nhiều)
MIN_TOTAL_RATINGS: int = 3  # Tăng từ 2

# Current
MIN_TOTAL_RATINGS: int = 2  # Balanced
```

### Level 2: Similarity Thresholds (content_based.py)

#### Similar Products Threshold

```python
# Line ~130 in _recommend_similar
if similarities[idx] < 0.15:  # Loose - more recall
if similarities[idx] < 0.2:   # Balanced (CURRENT)
if similarities[idx] < 0.3:   # Strict - more precision
```

#### Search History Threshold

```python
# Line ~175 in _recommend_from_search_history
if similarities[idx] < 0.1:   # Loose - more recall
if similarities[idx] < 0.15:  # Balanced (CURRENT)
if similarities[idx] < 0.25:  # Strict - more precision
```

### Level 3: Candidate Pool Size (hybrid.py)

```python
# Line ~45 in recommend()
n_items * 2.0   # Strict - fewer candidates, higher precision
n_items * 2.5   # Balanced (CURRENT)
n_items * 3.0   # Loose - more candidates, higher recall
```

### Level 4: Model Hyperparameters (config.py)

```python
# More components = better learning but slower
N_COMPONENTS: int = 10   # Fast, lower quality
N_COMPONENTS: int = 15   # Balanced (CURRENT)
N_COMPONENTS: int = 20   # Slow, higher quality

# More iterations = better convergence
MAX_ITER: int = 50    # Fast training
MAX_ITER: int = 100   # Balanced (CURRENT)
MAX_ITER: int = 200   # Better convergence
```

---

## 📈 Tuning Process

### Step 1: Identify Current State

```bash
POST http://localhost:8000/model/evaluate
```

Look at the metrics:

- **P > 45%, R < 40%** → Too strict, giảm thresholds
- **P < 30%, R > 60%** → Too loose, tăng thresholds
- **P = 35-45%, R = 45-55%** → Good balance! 🎯

### Step 2: Adjust ONE parameter at a time

**Example: If P=52%, R=33% (Current)**

```python
# Try 1: Giảm SCORE_THRESHOLD
SCORE_THRESHOLD: 0.25 → 0.2  # Dự đoán: P↓, R↑

# Train & Evaluate
POST /model/train
POST /model/evaluate

# Result: P=52%, R=33% → P=42%, R=48% ✓
```

### Step 3: Fine-tune if needed

**If P=42%, R=48% (Close but can be better)**

```python
# Try: Giảm MIN_RATING_THRESHOLD một chút
MIN_RATING_THRESHOLD: 3.0 → 2.8

# Train & Evaluate again
# Target: P=38-40%, R=50-53%
```

### Step 4: Verify with Real Recommendations

```bash
# Test với user thực
POST http://localhost:8000/recommendations/hybrid
{
  "user_id": "your_test_user_id"
}

# Check:
# - Có bao nhiêu recommendations?
# - Chúng có relevant không?
# - Mix của categories tốt không?
```

---

## 🎯 Target Metrics by Use Case

### E-commerce Cake Shop (Your Case)

```
Target: Precision = 38-42%, Recall = 48-55%
→ Balance giữa accuracy và discovery
→ Users see relevant cakes + discover new options
```

**Config:**

```python
SCORE_THRESHOLD: 0.2
MIN_RATING_THRESHOLD: 3.0
MIN_TOTAL_RATINGS: 2
Similarity threshold: 0.2
Candidate multiplier: 2.5
```

### High-End Luxury Products

```
Target: Precision = 50-60%, Recall = 35-45%
→ Prioritize accuracy over discovery
→ Only show highly relevant, premium items
```

**Config:**

```python
SCORE_THRESHOLD: 0.3
MIN_RATING_THRESHOLD: 4.0
MIN_TOTAL_RATINGS: 5
Similarity threshold: 0.35
Candidate multiplier: 2.0
```

### Discovery/Browse Heavy

```
Target: Precision = 25-35%, Recall = 60-70%
→ Show many options for exploration
→ Accept some less relevant items
```

**Config:**

```python
SCORE_THRESHOLD: 0.15
MIN_RATING_THRESHOLD: 2.5
MIN_TOTAL_RATINGS: 1
Similarity threshold: 0.15
Candidate multiplier: 3.5
```

---

## 🧪 Quick Test Scenarios

### Scenario A: "I want safer recommendations"

```python
SCORE_THRESHOLD: 0.2 → 0.25
MIN_RATING_THRESHOLD: 3.0 → 3.3
```

Expected: P↑ (by 5-8%), R↓ (by 3-5%)

### Scenario B: "I want more recommendations"

```python
SCORE_THRESHOLD: 0.2 → 0.15
candidate multiplier: 2.5 → 3.0
```

Expected: P↓ (by 5-10%), R↑ (by 8-12%)

### Scenario C: "Optimize for F1"

```python
# Try to maximize F1 = 2PR/(P+R)
# Usually achieved when P and R are close
Target: P ≈ R ≈ 45%

# Adjust to:
SCORE_THRESHOLD: 0.18
MIN_RATING_THRESHOLD: 3.1
candidate multiplier: 2.8
```

---

## 📊 Monitoring Dashboard (Mental Model)

```
High Precision Zone (P > 50%)
    ↑ Too strict, users see too few options
    │
Sweet Spot (P=35-45%, R=45-55%)
    │ ✅ Balanced, best UX
    │
High Recall Zone (R > 60%)
    ↓ Too loose, many irrelevant items
```

**Current Position:** Moving from High Precision → Sweet Spot

---

## 🔄 Iterative Tuning Workflow

```bash
# 1. Current metrics
POST /model/evaluate

# 2. Identify adjustment needed
# P too high? → decrease thresholds
# R too low? → increase candidate pool

# 3. Edit config.py
# Adjust ONE parameter

# 4. Retrain
POST /model/train

# 5. Re-evaluate
POST /model/evaluate

# 6. Compare with target
python compare_metrics.py

# 7. Repeat until satisfied
```

---

## 💡 Pro Tips

1. **Don't change multiple parameters at once**

   - Change one → measure impact → adjust next

2. **F1 score is your friend**

   - F1 balances P and R
   - Optimize for F1 > 40% as starting point

3. **Real user feedback > metrics**

   - Track actual CTR and conversions
   - A/B test different configs

4. **Dataset size matters**

   - Small dataset (< 100 orders): looser thresholds
   - Large dataset (> 1000 orders): stricter thresholds

5. **Retrain regularly**
   - Weekly with new data
   - Adjust thresholds as dataset grows

---

## 🎯 Quick Reference Card

| Metric                 | Value          | Action              |
| ---------------------- | -------------- | ------------------- |
| P > 50%, R < 35%       | **Too Strict** | Decrease thresholds |
| P < 30%, R > 60%       | **Too Loose**  | Increase thresholds |
| P = 35-45%, R = 45-55% | **Sweet Spot** | ✅ Keep config      |
| F1 > 42%               | **Good**       | Minor tuning only   |
| F1 < 35%               | **Needs work** | Major adjustment    |

---

## 🚀 Next Steps

1. **Train with new balanced config:**

   ```bash
   POST http://localhost:8000/model/train
   ```

2. **Evaluate:**

   ```bash
   POST http://localhost:8000/model/evaluate
   ```

3. **Target Results:**

   - Precision: 38-42%
   - Recall: 48-55%
   - F1: 42-47%

4. **If not satisfied, refer to tuning sections above**

5. **Deploy and monitor real usage:**
   - Track CTR
   - User feedback
   - Conversion rate
   - Adjust monthly based on real data
