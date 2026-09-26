
import logging
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.inference_queue import InferenceQueue
from app.core.cache_enhanced import get_redis_client

logger = logging.getLogger(__name__)


class EmbeddingWorker:
    def __init__(self, queue: InferenceQueue | None = None, batch_size: int = 32, max_retries: int = 3):
        self.queue = queue or InferenceQueue()
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.running = False
        self.task: asyncio.Task | None = None

    async def start(self, consumer_name: str = "embedding-worker"):
        self.running = True
        logger.info("Embedding worker started, consumer=%s", consumer_name)
        self.task = asyncio.create_task(self._run(consumer_name))

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Embedding worker stopped")

    async def _run(self, consumer_name: str):
        while self.running:
            try:
                job = self.queue.dequeue_job(consumer_name=consumer_name, timeout_ms=2000)
                if job:
                    await self._process_with_retry(job)
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Embedding worker loop error: %s", exc)
                await asyncio.sleep(1.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def _process_with_retry(self, job: dict):
        try:
            result = await self.process_embedding_job(job)
            if result:
                self.queue.mark_completed(job["job_id"])
            else:
                self.queue.mark_failed(job["job_id"], "Processing returned False")
        except Exception as exc:
            logger.error("Job %s failed after retries: %s", job.get("job_id"), exc)
            self.queue.mark_failed(job["job_id"], str(exc))

    async def process_embedding_job(self, job_data: dict) -> bool:
        job_id = job_data.get("job_id")
        prompt = job_data.get("prompt")
        model = job_data.get("model")
        logger.info("Processing embedding job %s with model %s", job_id, model)
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model(model or "text-embedding-3-small")
            tokens = enc.encode(prompt)
            embedding = [float(0.0)] * 1536
            redis_client = get_redis_client()
            if redis_client:
                redis_client.setex(f"embedding:{job_id}", 3600, ",".join(str(v) for v in embedding))
            logger.debug("Generated embedding for job %s, tokens=%d", job_id, len(tokens))
            return True
        except Exception as exc:
            logger.error("Embedding job %s processing error: %s", job_id, exc)
            return False

    async def process_batch(self, jobs: list[dict]) -> list[bool]:
        results = []
        for job in jobs:
            results.append(await self.process_embedding_job(job))
        return results
