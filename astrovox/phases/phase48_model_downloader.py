"""Remote model downloader."""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DownloadResult:
    """Result of a model download."""
    success: bool
    path: str = ""
    error: str = ""
    bytes_downloaded: int = 0

    def to_dict(self) -> dict:
        return {"success": self.success, "path": self.path, "error": self.error,
                "bytes_downloaded": self.bytes_downloaded}


class ModelDownloader:
    """Download models from remote URLs."""

    def __init__(self, cache_dir: str = "models/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_url(self, name: str, version: str) -> str:
        return f"https://models.astrovox.ai/{name}/{version}/model.pt"

    def download(self, name: str, version: str = "latest",
                 force: bool = False) -> DownloadResult:
        cached = self.cache_dir / name / version
        if cached.exists() and not force:
            return DownloadResult(success=True, path=str(cached))
        url = self._generate_url(name, version)
        if not url.startswith(("http://", "https://")):
            return DownloadResult(success=False, error="URL scheme not allowed")
        try:
            local, _ = urllib.request.urlretrieve(url, str(cached))  # nosec B310
            size = cached.stat().st_size if cached.exists() else 0
            return DownloadResult(success=True, path=str(cached), bytes_downloaded=size)
        except Exception as e:
            return DownloadResult(success=False, error=str(e))

    def download_many(self, requests: list[tuple[str, str]]) -> list[DownloadResult]:
        return [self.download(name, version) for name, version in requests]

    def clear_cache(self, name: str | None = None) -> None:
        if name is None:
            import shutil
            shutil.rmtree(self.cache_dir, ignore_errors=True)
            return
        import shutil
        shutil.rmtree(self.cache_dir / name, ignore_errors=True)
