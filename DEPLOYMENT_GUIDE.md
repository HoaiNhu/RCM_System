# RCM System - Deployment Guide (Updated với NMF)

## 🎯 Thay đổi chính

### ✅ Đã loại bỏ lightfm (có bug)

- **Cũ**: lightfm 1.17 (không build được, có bug `__LIGHTFM_SETUP__`)
- **Mới**: scikit-learn 1.6.0 với NMF (Non-negative Matrix Factorization)

### ✅ Nâng cấp công nghệ

- **Python**: 3.9 → 3.12
- **FastAPI**: 0.115.4 → 0.115.6
- **NumPy**: 1.24.3 → 2.2.0
- **SciPy**: 1.11.3 → 1.14.1
- **scikit-learn**: 1.3.2 → 1.6.0
- **Loại bỏ**: Cython (không cần thiết)

## 📦 Files đã cập nhật

### 1. requirements.txt

```txt
# Core ML libraries (Python 3.12 compatible)
numpy==2.2.0
scipy==1.14.1
scikit-learn==1.6.0
pandas==2.2.3

# FastAPI and web server (latest)
fastapi==0.115.6
uvicorn[standard]==0.32.1
pydantic==2.10.3

# Database and cache
pymongo==4.10.1
redis==5.2.1

# Utilities
python-dotenv==1.0.1
```

### 2. Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install build dependencies (minimal cho scikit-learn)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Copy và install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Environment variables
ENV PYTHONPATH=/app
ENV PORT=10000

EXPOSE $PORT

# Run application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
```

### 3. app/recommender.py

- Viết lại hoàn toàn với **sklearn.decomposition.NMF**
- Sử dụng matrix factorization thay vì lightfm
- User features (W matrix) và Product features (H matrix)
- Tính toán: `scores = user_features @ product_features.T`

## 🚀 Hướng dẫn Deploy

### Option 1: Docker Build Local

```bash
cd C:\Users\Lenovo\STUDY\RCM_System
docker build -t rcm-system:latest .
docker run -p 10000:10000 --env-file .env rcm-system:latest
```

### Option 2: Docker Compose (nếu có)

```bash
docker-compose up --build
```

### Option 3: Deploy lên Cloud

```bash
# Push to Docker Hub
docker tag rcm-system:latest <your-username>/rcm-system:latest
docker push <your-username>/rcm-system:latest

# Deploy to Render/Railway/Fly.io
# (Sử dụng Dockerfile trong repo)
```

## 🔍 Kiểm tra deployment

### Test local

```bash
curl http://localhost:10000/health
```

### Test API

```bash
# Recommend endpoint
curl -X POST http://localhost:10000/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": "123", "product_id": "456"}'

# Evaluate model
curl http://localhost:10000/evaluate-model
```

## 📊 Ưu điểm của NMF so với LightFM

1. **Stable**: scikit-learn rất ổn định, được maintain tốt
2. **No compilation errors**: Không cần compile C/C++ code
3. **Python 3.12 compatible**: Hoàn toàn tương thích
4. **Better performance**: NMF với nndsvd initialization rất tốt
5. **Easier debugging**: Pure Python, dễ debug hơn

## 🛠️ Troubleshooting

### Nếu build lâu:

- Build locally với cache: `docker build --progress=plain -t rcm-system .`
- Kiểm tra network connection

### Nếu thiếu dữ liệu:

- Model sẽ fallback về popular products
- Cần có ít nhất một số orders/ratings để train

## 📝 Notes

- Model được save vào `model.pkl` và `mappings.pkl`
- Precompute recommendations cho tối đa 100 users
- Cache recommendations trong Redis (3600s)
- Fallback strategy khi user mới hoặc không có model

## ✅ Ready to deploy!

Bây giờ bạn có thể:

1. Commit changes: `git add -A && git commit -m "Upgrade to NMF recommender system"`
2. Push: `git push`
3. Deploy trên platform của bạn (Render, Railway, etc.)
