"""Job handlers and event subscribers — wires the job queue and event bus."""

from .jobs import job_queue, Job, JobPriority, JobStatus
from .events import event_bus
from .metrics import track_ai_request


# ============================================================================
# Job Handlers
# ============================================================================

async def handle_embedding_job(job: Job):
    """Process an embedding generation job."""
    from .embedding.service import EmbeddingService

    texts = job.payload.get("texts", [])
    model = job.payload.get("model")
    provider = job.payload.get("provider", "openai")

    service = EmbeddingService(provider_name=provider, model=model)
    result = await service.embed_batch(texts)

    return {
        "embeddings_count": len(result.embeddings),
        "model": result.model,
        "provider": result.provider,
        "total_tokens": result.total_tokens,
    }


async def handle_memory_consolidation(job: Job):
    """Consolidate memories for a user."""
    user_id = job.payload.get("user_id", "")
    # Placeholder: would consolidate memories in a real implementation
    return {"user_id": user_id, "consolidated": 0}


async def handle_analytics_aggregation(job: Job):
    """Aggregate analytics data."""
    org_id = job.payload.get("organization_id", "")
    return {"organization_id": org_id, "aggregated": True}


async def handle_cleanup(job: Job):
    """Run cleanup tasks."""
    return {"cleaned": True}


# Register job handlers
job_queue.register_handler("embedding", handle_embedding_job)
job_queue.register_handler("memory_consolidation", handle_memory_consolidation)
job_queue.register_handler("analytics_aggregation", handle_analytics_aggregation)
job_queue.register_handler("cleanup", handle_cleanup)


# ============================================================================
# Event Subscribers
# ============================================================================

def on_conversation_created(event):
    """Handle conversation creation events."""
    pass  # Could trigger analytics, notifications, etc.


def on_memory_created(event):
    """Handle memory creation events."""
    pass  # Could trigger memory consolidation


def on_provider_failure(event):
    """Handle provider failure events."""
    provider = event.data.get("provider", "unknown")
    track_ai_request(model="unknown", status="error")


def on_user_login(event):
    """Handle user login events."""
    pass  # Could update presence, send notifications


# Subscribe to events
event_bus.subscribe("conversation.created", on_conversation_created)
event_bus.subscribe("memory.created", on_memory_created)
event_bus.subscribe("provider.failure", on_provider_failure)
event_bus.subscribe("user.login", on_user_login)
