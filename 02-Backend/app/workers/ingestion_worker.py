
import asyncio
import logging

from app.inference_queue import InferenceQueue
from app.core.cache_enhanced import get_redis_client

logger = logging.getLogger(__name__)


class IngestionWorker:
    def __init__(self, queue: InferenceQueue | None = None, chunk_size: int = 512, overlap: int = 50):
        self.queue = queue or InferenceQueue()
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.running = False
        self.task = None

    async def start(self, consumer_name: str = "ingestion-worker"):
        self.running = True
        logger.info("Ingestion worker started, consumer=%s", consumer_name)
        self.task = asyncio.create_task(self._run(consumer_name))

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Ingestion worker stopped")

    async def _run(self, consumer_name: str):
        while self.running:
            try:
                job = self.queue.dequeue_job(consumer_name=consumer_name, timeout_ms=2000)
                if job:
                    await self.process_ingestion_job(job)
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Ingestion worker loop error: %s", exc)
                await asyncio.sleep(1.0)

    async def process_ingestion_job(self, job_data: dict) -> bool:
        job_id = job_data.get("job_id")
        prompt = job_data.get("prompt")
        model = job_data.get("model")
        logger.info("Processing ingestion job %s", job_id)
        try:
            chunks = self._chunk_text(prompt)
            embeddings = []
            for chunk in chunks:
                embedding = await self._embed_chunk(chunk, model)
                embeddings.append(embedding)
            redis_client = get_redis_client()
            if redis_client:
                redis_client.setex(f"ingestion:{job_id}", 3600, str(len(chunks)))
            logger.debug("Ingested job %s, chunks=%d", job_id, len(chunks))
            return True
        except Exception as exc:
            logger.error("Ingestion job %s error: %s", job_id, exc)
            return False

    def _chunk_text(self, text: str) -> list[str]:
        if not text:
            return []
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + self.chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start = end - self.overlap
        return [c for c in chunks if c]

    async def _embed_chunk(self, text: str, model: str) -> list[float]:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(model or "text-embedding-3-small")
            enc.encode(text)
        except Exception:
            pass
        return [0.0] * 1536
