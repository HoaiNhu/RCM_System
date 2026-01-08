# 🎯 RCM System - Cải Thiện Precision & Recall

## 📊 Vấn Đề Ban Đầu

```
Precision: 0.1062 (10.6%) - RẤT THẤP
Recall:    0.6598 (66.0%) - KHÁ TỐT
F1 Score:  0.1829 (18.3%) - THẤP
```

**Precision thấp** = Hệ thống recommend quá nhiều sản phẩm không liên quan

---

## ✨ Các Cải Tiến Đã Thực Hiện

### 1️⃣ **Tăng Quality Thresholds**

```python
# config.py
MIN_RATING_THRESHOLD: 3.5  # Tăng từ 2.0
MIN_TOTAL_RATINGS: 2       # Mới - sản phẩm phải có ít nhất 2 reviews
SCORE_THRESHOLD: 0.3       # Mới - score tối thiểu để recommend
```

**Lý do:** Chỉ recommend sản phẩm chất lượng cao, được đánh giá tốt

### 2️⃣ **Score Threshold Filtering**

```python
# Trong collaborative_filtering.py
# Normalize scores và chỉ recommend nếu score >= 0.3
if normalized_scores[idx] < self.settings.SCORE_THRESHOLD:
    continue
```

**Lý do:** Loại bỏ recommendations có confidence thấp

### 3️⃣ **Similarity Thresholds**

```python
# content_based.py
# Chỉ recommend sản phẩm có similarity >= 0.3
if similarities[idx] < 0.3:
    continue
```

**Lý do:** Tránh recommend sản phẩm quá khác biệt

### 4️⃣ **Diversity Algorithm**

```python
# hybrid.py
# Tránh recommend quá nhiều sản phẩm từ cùng category
def _apply_diversity(self, product_ids, n_items):
    # Ưu tiên sản phẩm từ categories khác nhau
```

**Lý do:** Tăng variety cho user experience

### 5️⃣ **Tuned Hyperparameters**

```python
# config.py
N_COMPONENTS: 15   # Tăng từ 10
MAX_ITER: 100      # Tăng từ 50
```

**Lý do:** Model học tốt hơn với nhiều features và iterations

### 6️⃣ **Better Candidate Selection**

```python
# hybrid.py
# Giảm số candidates từ n*3 xuống n*2
cf_recommendations = self.cf_strategy.recommend(user_id, n_items=n_items * 2)
```

**Lý do:** Focus vào top candidates thay vì cast net rộng

---

## 🧪 Cách Test

### Bước 1: Backup metrics hiện tại

```bash
# 1. Evaluate model cũ và lưu kết quả
POST http://localhost:8000/model/evaluate

# 2. Copy response và save vào metrics_before.json
```

### Bước 2: Train model mới

```bash
# Train lại với improvements mới
POST http://localhost:8000/model/train
```

### Bước 3: Evaluate model mới

```bash
# Evaluate và lưu kết quả
POST http://localhost:8000/model/evaluate

# Save response vào metrics_after.json
```

### Bước 4: So sánh kết quả

```bash
python compare_metrics.py
```

---

## 📈 Kết Quả Kỳ Vọng

### Scenario 1: Precision Tăng, Recall Giảm Nhẹ (TỐT NHẤT)

```
Precision: 0.25-0.35 (+15-25 points) ✅
Recall:    0.55-0.65 (-5 points)     ✓
F1:        0.35-0.45 (+15-25 points) ✅
```

**Giải thích:** Đây là trade-off tốt - ít recommendations nhưng chính xác hơn

### Scenario 2: Cả Hai Đều Tăng (HOÀN HẢO)

```
Precision: 0.30+ ✅
Recall:    0.65+ ✅
F1:        0.40+ ✅
```

**Giải thích:** Improvement hoàn hảo nhờ viewCount/clickCount signals

### Scenario 3: Cả Hai Đều Giảm (CẦN TUNE)

```
Precision: < 0.10 ❌
Recall:    < 0.50 ❌
```

**Giải thích:** Thresholds quá cao, cần giảm xuống

---

## 🔧 Nếu Kết Quả Chưa Tốt

### Nếu Precision vẫn thấp (< 0.20):

```python
# config.py
SCORE_THRESHOLD: float = 0.4  # Tăng từ 0.3
MIN_RATING_THRESHOLD: float = 4.0  # Tăng từ 3.5
```

### Nếu Recall giảm quá nhiều (< 0.50):

```python
# config.py
SCORE_THRESHOLD: float = 0.2  # Giảm từ 0.3
MIN_RATING_THRESHOLD: float = 3.0  # Giảm từ 3.5
MIN_TOTAL_RATINGS: int = 1  # Giảm từ 2
```

### Nếu cần balance:

```python
# hybrid.py - Điều chỉnh weights
self.cf_weight = 0.6  # Giảm từ 0.7
self.content_weight = 0.4  # Tăng từ 0.3
```

---

## 🎯 Target Metrics

**Tốt:**

- Precision: 0.25-0.30
- Recall: 0.55-0.60
- F1: 0.35-0.40

**Xuất Sắc:**

- Precision: 0.35+
- Recall: 0.60+
- F1: 0.45+

---

## 💡 Tips

1. **Monitor trong production:**

   - Track click-through rate (CTR)
   - User feedback
   - Conversion rate

2. **A/B Testing:**

   - Test với 50% users
   - Compare metrics sau 1 tuần

3. **Continuous Improvement:**

   - Retrain weekly với data mới
   - Adjust thresholds theo feedback

4. **Log recommendations:**
   ```python
   # Thêm logging để debug
   print(f"User {user_id}: {len(recommendations)} recommendations")
   print(f"Avg score: {np.mean(scores):.3f}")
   ```

---

## 📝 Checklist

- [ ] Backup metrics hiện tại vào `metrics_before.json`
- [ ] Review code changes trong 3 files:
  - `app/core/config.py`
  - `app/services/collaborative_filtering.py`
  - `app/services/hybrid.py`
- [ ] Train model mới: `POST /model/train`
- [ ] Evaluate: `POST /model/evaluate`
- [ ] Save kết quả vào `metrics_after.json`
- [ ] Run comparison: `python compare_metrics.py`
- [ ] Test recommendations thực tế trong Postman
- [ ] Fine-tune nếu cần thiết

---

## 🚀 Expected Impact

| Metric    | Before | After  | Improvement       |
| --------- | ------ | ------ | ----------------- |
| Precision | 10.6%  | 25-35% | **+15-25 points** |
| Recall    | 66.0%  | 55-65% | -5 to +0 points   |
| F1 Score  | 18.3%  | 35-45% | **+15-25 points** |

**Bottom Line:** Ít recommendations hơn nhưng CHÍNH XÁC hơn nhiều! 🎯
