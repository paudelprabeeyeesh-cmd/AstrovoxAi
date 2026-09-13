import hashlib
import json

try:
    import redis
    r = redis.Redis()
except Exception:
    r = None

def cached(key, fn):
    if r is None:
        return fn(key)
    k = hashlib.sha256(key.encode()).hexdigest()
    if r.exists(k):
        return json.loads(r.get(k))
    result = fn(key)
    r.set(k, json.dumps(result), ex=3600)
    return result
