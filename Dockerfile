FROM python:3.12-slim AS builder  
WORKDIR /app  
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    rustc \
    cargo \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/* 
  
COPY 02-Backend/requirements.txt .  
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && pip install --no-cache-dir --prefer-binary -r requirements.txt 
  
FROM python:3.12-slim  
WORKDIR /app  
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app  
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages  
COPY 02-Backend/app/ ./app/  
COPY 02-Backend/scripts/ ./scripts/ 

HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
