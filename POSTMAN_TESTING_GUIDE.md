# 🧪 Postman Testing Guide - RCM System API v2.0

## 📦 Quick Setup

### 1. Import vào Postman

**Option A: Import Collection & Environment**

1. Mở Postman
2. Click **Import** button
3. Kéo thả 2 files:
   - `RCM_System_API.postman_collection.json`
   - `RCM_System_Local.postman_environment.json`

**Option B: Import từ Git**

```bash
git clone <your-repo>
cd RCM_System
# Mở Postman và import 2 files JSON trong thư mục này
```

### 2. Chọn Environment

1. Ở góc trên bên phải Postman
2. Chọn **"RCM System - Local"**
3. Verify base_url = `http://localhost:8000`

### 3. Start Server

```powershell
cd c:\Users\Lenovo\STUDY\RCM_System
python run.py
```

Đợi đến khi thấy:

```
============================================================
🎉 SERVER IS READY TO ACCEPT REQUESTS!
📍 API Documentation: http://localhost:8000/docs
🔍 Health Check: http://localhost:8000/health
============================================================
```

---

## 🎯 Testing Flow (Recommended Order)

### ✅ Step 1: Health Checks

Test để verify server đang chạy và model đã load.

1. **✅ Root - API Info**
   - Expect: `{"message": "RCM System API v2.0", "status": "running"}`
2. **🏥 Health Check (Full)**
   - Expect: `"mongodb": "connected"` và `"model.ready": true`
3. **📊 Model Status**
   - Expect: Details về CF và Content-Based models

### 🎯 Step 2: Main Features - Recommendations

#### Test Basic Recommendations

4. **🎯 Hybrid Recommendations - For User Only**

   - Test personalized recommendations
   - Expect: Array of 5 product IDs

5. **🎯 Hybrid Recommendations - With Product Context**
   - Test context-aware recommendations
   - Expect: Similar products (không có product hiện tại)

#### Test Popular Products

6. **🔥 Popular Products - All Categories**

   - Test trending products
   - Expect: Top 10 popular products

7. **🔥 Popular Products - By Category**
   - Test category filtering
   - Expect: Top products trong category cụ thể

#### Test Quiz System

8. **📝 Quiz-based Recommendations**
   - Test quiz recommendations (nếu có quiz data)

#### Comparison Testing

9. **🧪 Test - Recommendations for Different Users**
   - So sánh recommendations giữa các users
   - Thử với `user_id_1`, `user_id_2`, `user_id_3`

### 📊 Step 3: Model Management

10. **📊 Evaluate Model Performance**

    - Check precision, recall, F1 score
    - Expect metrics > 0.6 is good

11. **🔄 Update Model** (Optional)

    - Update model với data mới
    - ⚠️ Mất vài phút

12. **🔨 Train Model** (Optional)
    - Full retrain từ đầu
    - ⚠️ Mất 5-10 phút

### 🔍 Step 4: Debug & Data Verification

13. **🔌 Debug - Connection Info**

    - Verify database collections

14. **📈 Debug - Data Statistics**

    - Check data counts

15. **📝 Log User Interaction**

    - Test logging system

16. **🧪 Test - Get Product/User by ID**
    - Verify data structure

---

## 📋 Environment Variables

File `RCM_System_Local.postman_environment.json` chứa:

```json
{
  "base_url": "http://localhost:8000",
  "user_id_1": "6756e4441df899603742e267",
  "user_id_2": "676eaf5cbf34ce78983409c3",
  "user_id_3": "677352004c7e2661dce1596a",
  "product_id_1": "67765db11f858633ea5ba243",
  "product_id_2": "67763afa608c0d719eb38d0c",
  "category_id_1": "675dad6116f7337d86806c27"
}
```

### 🔧 Cập nhật IDs cho database của bạn

1. Get real IDs từ database:

```bash
# MongoDB shell or Compass
db.users.find().limit(3)
db.products.find().limit(3)
db.categories.find().limit(3)
```

2. Update trong Postman Environment:
   - Click vào Environment name
   - Edit values
   - Save

---

## 🎨 Response Examples

### ✅ Successful Recommendation Response

```json
{
  "recommendations": [
    "67765db11f858633ea5ba243",
    "67763afa608c0d719eb38d0c",
    "67765db11f858633ea5ba244",
    "67763afa608c0d719eb38d0d",
    "67765db11f858633ea5ba245"
  ],
  "source": "hybrid (CF + Content-Based)",
  "user_id": "6756e4441df899603742e267"
}
```

### 📊 Model Evaluation Response

```json
{
  "metrics": {
    "precision@5": 0.82,
    "recall@5": 0.65,
    "f1@5": 0.72,
    "coverage": 0.85
  },
  "model_info": {
    "users": 25,
    "products": 37,
    "interactions": 450
  },
  "evaluated_at": "2024-11-20T10:30:00Z"
}
```

### 🏥 Health Check Response

```json
{
  "status": "healthy",
  "mongodb": "connected",
  "redis": "not configured",
  "model": {
    "ready": true,
    "cf_ready": true,
    "content_based_ready": true,
    "last_update": "2024-11-20T10:00:00Z"
  },
  "timestamp": "2024-11-20T10:30:00Z"
}
```

---

## 🐛 Common Issues & Solutions

### ❌ Problem: "Connection refused" error

**Solution:**

```powershell
# Check if server is running
netstat -ano | findstr :8000

# If not running, start server
python run.py
```

### ❌ Problem: "Model not ready"

**Solution:**

```powershell
# Wait for model initialization (check terminal logs)
# Or manually train model
POST http://localhost:8000/model/train
```

### ❌ Problem: "No recommendations found"

**Solutions:**

1. Check if user exists in database
2. Check if user has any interactions (orders/ratings)
3. Model might be in training - check `/health` endpoint

### ❌ Problem: 404 "User not found"

**Solution:**

```powershell
# Get valid user IDs from database
# Update Postman environment variables with real IDs
```

### ❌ Problem: Empty recommendations array

**Possible causes:**

1. User is new (no history) → Will get popular products
2. Product is not rated yet → Content-based will handle
3. Model needs more data → Add more interactions

---

## 🚀 Advanced Testing

### Load Testing with Multiple Users

```javascript
// Postman Pre-request Script
pm.environment.set("test_user", "user_" + Math.floor(Math.random() * 100));
```

### Test Response Time

1. Gửi multiple requests
2. Check "Time" column
3. Should be < 500ms for cached responses
4. < 2000ms for uncached

### Test Cache Behavior

1. Gửi same request 2 lần
2. First request: `"source": "hybrid"`
3. Second request: `"source": "cache"`
4. Response time should be faster

---

## 📚 API Documentation

### Interactive Docs (Swagger UI)

```
http://localhost:8000/docs
```

### Alternative Docs (ReDoc)

```
http://localhost:8000/redoc
```

---

## 💡 Tips & Best Practices

### ✅ DO:

- Test health check trước
- Sử dụng environment variables cho IDs
- Check terminal logs khi có errors
- Test với multiple users để verify personalization
- Cache clearing test để verify real-time updates

### ❌ DON'T:

- Hard-code IDs trong requests
- Train model quá thường xuyên (resource intensive)
- Ignore error messages
- Test production endpoints từ Postman (use staging)

---

## 📞 Support

### Check Logs

```powershell
# Server logs in terminal where you ran `python run.py`
# Look for ERROR messages
```

### Debug Mode

```powershell
# Enable verbose logging
$env:DEBUG="true"
python run.py
```

### Health Check API

```bash
curl http://localhost:8000/health
```

---

## 🎉 Happy Testing!

Questions? Check:

- `/docs` - Interactive API documentation
- `README.md` - Project documentation
- `ARCHITECTURE_V2.md` - System architecture

---

**Last Updated:** November 20, 2024
**API Version:** 2.0.0
**Author:** RCM System Team
