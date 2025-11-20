# 🚀 Quick Test Guide - RCM System

## ⚡ 5-Minute Test Flow

### 1. Start Server

```powershell
cd c:\Users\Lenovo\STUDY\RCM_System
python run.py
```

### 2. Import vào Postman

- `RCM_System_API.postman_collection.json`
- `RCM_System_Local.postman_environment.json`
- Select environment: **RCM System - Local**

### 3. Test (按順序)

| #   | Test                      | Expected                 |
| --- | ------------------------- | ------------------------ |
| 1   | ✅ Root - API Info        | `status: running`        |
| 2   | 🏥 Health Check           | `mongodb: connected`     |
| 3   | 🎯 Hybrid Recommendations | Array of 5 products      |
| 4   | 🔥 Popular Products       | Top 10 products          |
| 5   | 📊 Model Status           | CF & Content-Based ready |

---

## 📋 API Endpoints Cheat Sheet

### Health & Status

```http
GET  /                  # API info
GET  /health            # Full health check
GET  /status            # Model status
```

### Recommendations

```http
POST /recommend         # Hybrid recommendations
POST /recommend/popular # Popular products
POST /recommend/quiz    # Quiz-based
```

### Model Management

```http
GET  /model/evaluate    # Model metrics
POST /model/update      # Update model
POST /model/train       # Full retrain
```

### Debug

```http
GET  /debug/connection  # DB info
GET  /debug/data        # Data counts
POST /debug/interaction/log  # Log interaction
```

---

## 🎯 Test Examples

### Get Recommendations

```json
POST /recommend
{
  "user_id": "6756e4441df899603742e267",
  "n_items": 5
}
```

### Popular by Category

```json
POST /recommend/popular
{
  "category": "675dad6116f7337d86806c27",
  "n_items": 10
}
```

### Context-Aware

```json
POST /recommend
{
  "user_id": "6756e4441df899603742e267",
  "product_id": "67765db11f858633ea5ba243"
}
```

---

## 🔧 Environment Variables

Update trong Postman Environment:

```
base_url = http://localhost:8000
user_id_1 = <your_user_id>
product_id_1 = <your_product_id>
category_id_1 = <your_category_id>
```

---

## 🐛 Quick Troubleshooting

| Problem               | Solution                       |
| --------------------- | ------------------------------ |
| Connection refused    | Start server: `python run.py`  |
| Model not ready       | Wait 2-3 seconds or check logs |
| 404 User not found    | Update user IDs in environment |
| Empty recommendations | User needs interaction history |

---

## 📚 Full Documentation

- **Detailed Guide:** `POSTMAN_TESTING_GUIDE.md`
- **API Docs:** http://localhost:8000/docs
- **Architecture:** `ARCHITECTURE_V2.md`

---

**Server Status Check:**

```powershell
curl http://localhost:8000/health
```

**View Logs:** Check terminal where `python run.py` is running
