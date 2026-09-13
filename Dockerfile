FROM python:3.12-slim AS builder
WORKDIR /app
COPY 02-Backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY 02-Backend/app/ ./app/
COPY 02-Backend/scripts/ ./scripts/
ENV ASTROVOX_DB=/data/astrovox.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
