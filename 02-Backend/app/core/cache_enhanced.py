
import os, json
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

_redis_client = None

def get_redis_client():
    global _redis_client
    if not REDIS_AVAILABLE: return None
    if _redis_client is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.Redis.from_url(url, decode_responses=True)
    return _redis_client

def cache_get(key: str):
    client = get_redis_client()
    if not client: return None
    value = client.get(key)
    return json.loads(value) if value else None

def cache_set(key: str, value, ttl: int = 300):
    client = get_redis_client()
    if not client: return
    client.setex(key, ttl, json.dumps(value))

def cache_delete(key: str):
    client = get_redis_client()
    if not client: return
    client.delete(key)
