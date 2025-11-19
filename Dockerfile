FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libc-dev \
    libopenblas-dev \
    python3-dev \
    libomp-dev \
    gfortran \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

# Install numpy, scipy, cython first (required for lightfm)
RUN pip install --no-cache-dir numpy==1.26.4 scipy==1.14.1 cython==3.0.11

COPY requirements.txt .

# THÊM FLAG NÀY - quan trọng!
RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt

COPY app/ ./app/

ENV PYTHONPATH=/app
ENV PORT=10000

EXPOSE $PORT

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]