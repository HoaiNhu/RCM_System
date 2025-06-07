Recommendation System API
A FastAPI-based recommendation system deployed on Render, using MongoDB and Redis for data storage and caching.
Prerequisites

MongoDB Atlas account with webbuycake database.
Upstash Redis account for caching.
Render account for deployment.
Git installed locally.

Setup Locally

Clone the repository:git clone <your-repo-url>
cd recommendation-system

Create a .env file based on .env.example and fill in your credentials.
Install dependencies:pip install -r requirements.txt

Run the app:uvicorn app.main:app --reload

Access the API at http://localhost:8000/docs.

Deploy to Render

Create a new Web Service on Render.
Connect your GitHub repository.
Configure:
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Environment Variables: Add MONGODB_USERNAME, MONGODB_PASSWORD, UPSTASH_REDIS_HOST, UPSTASH_REDIS_PORT, UPSTASH_REDIS_PASSWORD.

Deploy the service.

API Endpoints

GET /: Welcome message.
GET /health: Health check.
POST /recommend: Get recommendations for a user and product.
POST /recommend/popular: Get popular products.
GET /evaluate-model: Evaluate the model.
POST /update-model: Update the recommendation model.
POST /interaction/log: Log user interactions.

Notes

Ensure MongoDB and Redis credentials are secure.
Model training may take time with large datasets.
