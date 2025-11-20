# RCM System v2.0 - Architecture Documentation

## 📋 Overview

RCM System v2.0 là hệ thống recommendation hoàn toàn mới được refactor theo **Clean Architecture** và **SOLID principles**, kết hợp **Hybrid Recommendation** giữa Collaborative Filtering và Content-Based Filtering.

## 🏗️ Architecture

### Layered Architecture

```
┌─────────────────────────────────────────┐
│         API Layer (FastAPI)             │  ← HTTP endpoints
├─────────────────────────────────────────┤
│       Service Layer (Business Logic)    │  ← Recommendation strategies
├─────────────────────────────────────────┤
│    Repository Layer (Data Access)       │  ← MongoDB operations
├─────────────────────────────────────────┤
│         Core Layer (Config & DI)        │  ← Configuration & Dependencies
└─────────────────────────────────────────┘
```

### Directory Structure

```
app/
├── core/                      # Core configuration & dependencies
│   ├── config.py             # Settings with pydantic-settings
│   └── dependencies.py       # Dependency injection (Singleton pattern)
│
├── repositories/              # Data Access Layer
│   ├── base.py               # IRepository interface & BaseRepository
│   └── repositories.py       # Concrete repositories:
│                              - UserRepository
│                              - ProductRepository
│                              - OrderRepository
│                              - RatingRepository
│                              - SearchHistoryRepository
│                              - QuizResponseRepository
│                              - ModelMetadataRepository
│
├── services/                  # Business Logic Layer
│   ├── base.py               # Strategy interfaces (IRecommendationStrategy)
│   ├── collaborative_filtering.py   # CF using NMF
│   ├── content_based.py      # Content-Based using TF-IDF
│   ├── hybrid.py             # Hybrid strategy (weighted combination)
│   └── additional_services.py # QuizRecommendationService, PopularProductService
│
├── api/                       # API Layer
│   └── v1/
│       ├── health.py         # Health & status endpoints
│       ├── recommendations.py # Recommendation endpoints
│       ├── model.py          # Model management endpoints
│       └── debug.py          # Debug & testing endpoints
│
├── schemas/                   # Request/Response schemas
│   └── __init__.py           # Pydantic models for validation
│
└── main.py                    # FastAPI application entry point
```

## 🎯 SOLID Principles Applied

### 1. Single Responsibility Principle (SRP)

- **Each class has one reason to change**
- `CollaborativeFilteringStrategy` → Chỉ xử lý CF recommendations
- `ContentBasedFilteringStrategy` → Chỉ xử lý Content-Based recommendations
- `ProductRepository` → Chỉ xử lý data access cho products
- Mỗi route file (`health.py`, `recommendations.py`) → Một nhóm chức năng cụ thể

### 2. Open/Closed Principle (OCP)

- **Open for extension, closed for modification**
- `IRecommendationStrategy` interface cho phép thêm strategies mới (e.g., DeepLearningStrategy) mà không sửa code cũ
- `BaseRepository` có thể extend cho các collection mới

### 3. Liskov Substitution Principle (LSP)

- **Subtypes must be substitutable for their base types**
- Tất cả strategies implement `IRecommendationStrategy` có thể thay thế nhau
- `CollaborativeFilteringStrategy`, `ContentBasedFilteringStrategy` đều có thể dùng trong `HybridRecommendationStrategy`

### 4. Interface Segregation Principle (ISP)

- **Many specific interfaces better than one general-purpose interface**
- `IRecommendationStrategy` → recommend, get_scores, is_ready
- `IModelTrainer` → train, evaluate (riêng biệt)
- Repositories có methods cụ thể cho từng collection

### 5. Dependency Inversion Principle (DIP)

- **Depend on abstractions, not concretions**
- `HybridRecommendationStrategy` depends on `IRecommendationStrategy` interface, không depend trực tiếp vào CF hay Content-Based
- FastAPI routes depend on `Depends()` injection, không tạo instances trực tiếp
- Services receive repositories qua constructor injection

## 🧠 Hybrid Recommendation System

### Architecture

```
                    User Request
                         ↓
              HybridRecommendationStrategy
                    ↙         ↘
    CollaborativeFiltering   ContentBasedFiltering
         (NMF)                (TF-IDF + Cosine)
            ↓                        ↓
      CF Scores                CB Scores
            ↓                        ↓
              Weighted Combination
                (0.7 CF + 0.3 CB)
                         ↓
              Consensus Boost (+20%)
                         ↓
              Final Recommendations
```

### Components

#### 1. Collaborative Filtering (CF)

- **Algorithm**: Non-negative Matrix Factorization (NMF)
- **Features**:
  - User-item interaction matrix from orders & ratings
  - **Search history integration** (NEW): +0.5 weight per search
  - Comment sentiment analysis
  - Matrix: Users × Products → Latent factors
- **Weight**: 70% trong hybrid

#### 2. Content-Based Filtering (CB)

- **Algorithm**: TF-IDF + Cosine Similarity
- **Features**:
  - Product text features (name, description, category)
  - User search keywords extraction
  - Similar product recommendations
- **Weight**: 30% trong hybrid

#### 3. Hybrid Strategy

- **Scoring**: `score = 0.7 × CF_score + 0.3 × CB_score`
- **Consensus boost**: +20% nếu cả CF và CB đều recommend product đó
- **Normalization**: Scores được normalize về [0, 1] trước khi combine
- **Fallback**: Nếu một strategy không available, dùng strategy còn lại

### Search History Integration (NEW)

```python
# In CollaborativeFilteringStrategy._prepare_interaction_matrix()
for user_id in all_users:
    searched_products = search_repo.get_searched_product_ids(user_id)
    for product_id in searched_products:
        interactions[user_idx, product_idx] += 0.5  # Search weight
```

**Benefits**:

- Tăng độ chính xác bằng cách sử dụng search behavior
- Products user đã search sẽ có higher scores
- Kết hợp với orders và ratings cho comprehensive profile

## 🔄 Data Flow

### Recommendation Request Flow

```
1. Client → POST /recommend {user_id, product_id?, n_items}
2. API Route → Check Redis cache
3. If cached → Return cached results
4. If not cached:
   a. HybridStrategy.recommend()
   b. Get CF candidates (user features @ product features)
   c. Get CB candidates (TF-IDF similarity)
   d. Score all candidates with weighted combination
   e. Apply consensus boost
   f. Sort and return top N
5. Cache results in Redis (TTL: 1 hour)
6. Return RecommendationResponse
```

### Model Training Flow

```
1. Startup → Background thread starts
2. Check if model exists on disk
3. If exists → Load from pickle files
4. If not:
   a. Prepare interaction matrix (orders + ratings + search history)
   b. Train NMF model (n_components=20, max_iter=500)
   c. Build TF-IDF features for products
   d. Save models to disk
5. Mark model as ready
6. App ready to serve requests
```

## 📊 Key Improvements

### 1. Clean Architecture

- **Separation of concerns**: API ↔ Service ↔ Repository ↔ Data
- **Testability**: Each layer có thể test độc lập
- **Maintainability**: Dễ dàng modify/extend từng layer

### 2. SOLID Principles

- **Flexible**: Thêm strategies mới không cần sửa code cũ
- **Reusable**: Repository pattern dùng lại cho nhiều services
- **Decoupled**: Dependencies inject qua interfaces

### 3. Hybrid Recommendations

- **Better accuracy**: Kết hợp CF + CB
- **Robust**: Fallback khi một strategy fail
- **Personalized**: CF cho user patterns + CB cho item similarity

### 4. Search History Integration

- **More context**: Sử dụng search behavior
- **Implicit feedback**: Không cần explicit ratings
- **Better cold start**: Content-based fallback for new users

### 5. Modular Routes

- **Organized**: Routes grouped by functionality
- **Versioned**: `/api/v1/` structure for future versions
- **Documented**: Auto-generated OpenAPI docs

## 🚀 Usage

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Migrate to new architecture (backup old code)
python app/migrate.py
```

### Running

```bash
# Development
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### API Endpoints

#### Health & Status

- `GET /` - Root endpoint
- `GET /health` - Health check (DB, Redis, Model status)
- `GET /status` - Detailed model status

#### Recommendations

- `POST /recommend` - Hybrid recommendations
- `POST /recommend/popular` - Popular products
- `POST /recommend/quiz` - Quiz-based recommendations

#### Model Management

- `GET /model/evaluate` - Evaluate model metrics
- `POST /model/update` - Trigger background training
- `POST /model/train` - Train model synchronously

#### Debug & Testing

- `GET /debug/connection` - Test connections
- `GET /debug/data` - Data statistics
- `POST /debug/interaction/log` - Log user interaction

### Example Request

```bash
# Get hybrid recommendations
curl -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "6756e4441df899603742e267",
    "n_items": 5
  }'

# Response
{
  "recommendations": ["67765db11f858633ea5ba243", ...],
  "source": "hybrid (CF + Content-Based)",
  "user_id": "6756e4441df899603742e267"
}
```

## 📈 Performance

### Caching Strategy

- **Redis cache** cho recommendations (TTL: 1 hour)
- **Model persistence** với pickle files
- **Lazy loading** strategies (load only when needed)

### Background Training

- **Non-blocking**: Model trains in background thread
- **Fast startup**: App starts in <5 seconds
- **Graceful degradation**: Serves fallback recommendations during training

## 🧪 Testing

### Postman Collection

- Import `RCM_System_API.postman_collection.json`
- Use `RCM_System_Local.postman_environment.json` for local testing
- Use `RCM_System_Production.postman_environment.json` for production

### Test Scenarios

1. Health check → Verify all systems connected
2. Get recommendations → Test hybrid strategy
3. Popular products → Test fallback
4. Model evaluation → Check metrics
5. Debug endpoints → Verify data

## 📚 References

### Design Patterns Used

- **Strategy Pattern**: Recommendation strategies
- **Repository Pattern**: Data access
- **Singleton Pattern**: Settings, dependencies
- **Dependency Injection**: FastAPI Depends()
- **Factory Pattern**: Service creation in dependencies.py

### Technologies

- **FastAPI**: Modern async web framework
- **scikit-learn**: ML algorithms (NMF, TF-IDF)
- **NumPy/SciPy**: Numerical computing
- **MongoDB**: NoSQL database
- **Redis**: Caching layer
- **Pydantic**: Data validation

## 🔮 Future Enhancements

1. **Deep Learning Strategy**: Add neural network-based recommendations
2. **A/B Testing**: Framework for comparing strategies
3. **Real-time Training**: Incremental model updates
4. **Multi-armed Bandit**: Exploration vs exploitation
5. **Graph-based Recommendations**: User-product graph
6. **Explainable AI**: Provide recommendation reasons

## 📝 Migration Notes

### Old Code → New Code Mapping

| Old File         | New Location                                                                             | Notes                           |
| ---------------- | ---------------------------------------------------------------------------------------- | ------------------------------- |
| `utils.py`       | `core/config.py`, `repositories/`                                                        | Tách thành config & data access |
| `models.py`      | `schemas/__init__.py`                                                                    | Pydantic schemas only           |
| `recommender.py` | `services/collaborative_filtering.py`, `services/content_based.py`, `services/hybrid.py` | Tách thành 3 strategies         |
| `main.py`        | `main.py`, `api/v1/*.py`                                                                 | FastAPI app + modular routes    |

### Breaking Changes

- API structure remains the same (backward compatible)
- Internal architecture completely refactored
- All endpoints work as before but with better performance

### Backward Compatibility

✅ All existing endpoints maintained
✅ Request/response formats unchanged
✅ Postman collection still works
✅ Deployed apps continue working

---

**Version**: 2.0.0  
**Author**: RCM System Team  
**Date**: 2025-01-19  
**Status**: Production Ready ✅
