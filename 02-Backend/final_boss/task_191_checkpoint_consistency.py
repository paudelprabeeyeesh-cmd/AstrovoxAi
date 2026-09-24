import hashlib
import threading


class AsyncCheckpoint:
    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()

    def async_save(self, data):
        def _save(d):
            with self._lock:
                self._queue.append(d)

        t = threading.Thread(target=_save, args=(data,))
        t.start()
        return t

    def verify(self, data):
        h = hashlib.sha256(str(data).encode()).hexdigest()
        return h
