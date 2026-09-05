# Production Dockerfile for MedLens
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create uploads directory
RUN mkdir -p uploads

EXPOSE 8000

# Start Uvicorn server using dynamic PORT environment variable for Google Cloud Run
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
