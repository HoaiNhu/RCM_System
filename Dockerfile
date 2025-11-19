FROM python:3.10

WORKDIR /app

# Install minimal dependencies for Python 3.9 (has pre-built wheels)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libopenblas-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ENV PYTHONPATH=/app
ENV PORT=10000

EXPOSE $PORT

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]