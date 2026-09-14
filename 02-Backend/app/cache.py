import hashlib
import json

_r = None

def _get_redis():
    global _r
    if _r is None:
        try:
            import redis
            _r = redis.Redis()
            _r.exists("test")
        except Exception:
            _r = None
    return _r

def cached(key, fn):
    r = _get_redis()
    if r is None:
        return fn(key)
    k = hashlib.sha256(key.encode()).hexdigest()
    if r.exists(k):
        return json.loads(r.get(k))
    result = fn(key)
    r.set(k, json.dumps(result), ex=3600)
    return result
