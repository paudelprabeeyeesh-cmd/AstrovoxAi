import hashlib
from pathlib import Path
from typing import BinaryIO, Optional, Union


class FileStore:
    def __init__(self, root: Union[str, Path]) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        safe = key.replace("/", "_").replace("\\", "_")
        return self.root / safe

    def put(self, key: str, data: Union[bytes, BinaryIO]) -> Path:
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(data, "read"):
            dest.write_bytes(data.read())
        else:
            dest.write_bytes(data)
        return dest

    def get(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"Key not found: {key}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def size(self, key: str) -> int:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"Key not found: {key}")
        return path.stat().st_size

    def checksum(self, key: str) -> str:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"Key not found: {key}")
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
