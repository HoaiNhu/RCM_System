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