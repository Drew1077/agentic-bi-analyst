FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY sql ./sql
COPY semantic_layer ./semantic_layer
COPY docs ./docs
COPY pytest.ini ./

# Data is intentionally not copied into the image.
# Compose mounts ./data into /app/data for the one-shot loader.
RUN mkdir -p /app/data

EXPOSE 8000 8501

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
