FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-devel AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY 02-Backend/app/ ./app/
COPY ASTROVOX_AI/ai_core/inference/ ./ai_core/inference/
COPY infrastructure/docker/inference/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

EXPOSE 8001 8002

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "app.inference_engine"]
