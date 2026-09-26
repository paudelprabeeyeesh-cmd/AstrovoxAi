"""Video Search — search for video content across web and internal sources."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.web_search import web_search

logger = logging.getLogger(__name__)


def search_videos(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    search_variants = [
        f"{query} video",
        f"{query} tutorial",
        f"{query} watch online",
        f"youtube {query}",
    ]
    seen = set()
    results = []
    for variant in search_variants:
        try:
            hits = web_search.search(variant, max_results=top_k)
            for hit in hits:
                key = hit.url or hit.title
                if key and key not in seen:
                    seen.add(key)
                    results.append({
                        "title": hit.title,
                        "url": hit.url,
                        "snippet": hit.snippet,
                        "score": float(hit.score or 0.0),
                        "source": "video_web_search",
                        "description": hit.snippet,
                        "published_at": "",
                        "thumbnail": "",
                        "duration": None,
                    })
        except Exception as exc:
            logger.debug("Video search variant failed: %s", exc)
    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return results[:top_k]


def search_internal_videos(user_id: str, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    try:
        from app.video_intelligence import VideoSearchEngine
        engine = VideoSearchEngine()
        return engine.search(query, user_id=user_id, top_k=top_k)
    except Exception:
        return []


def extract_video_captions(video_bytes: bytes, filename: str = "", with_scenes: bool = False) -> Dict[str, Any]:
    from app.search_knowledge import VideoCaptionExtractor
    extractor = VideoCaptionExtractor()
    if with_scenes:
        return {
            "captions": extractor.extract(video_bytes, filename),
            "scenes": extractor.extract_scene_descriptions(video_bytes),
        }
    return extractor.extract(video_bytes, filename)


class VideoSearchEngine:
    def search(self, query: str, user_id: str = "system", top_k: int = 10) -> List[Dict[str, Any]]:
        web_videos = search_videos(query, top_k)
        internal_videos = search_internal_videos(user_id, query, top_k)
        combined = web_videos + internal_videos
        seen = set()
        unique = []
        for item in combined:
            key = item.get("url") or item.get("title")
            if key and key not in seen:
                seen.add(key)
                unique.append(item)
        unique.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return unique[:top_k]

    def extract_captions(self, video_bytes: bytes, filename: str = "", with_scenes: bool = False) -> Dict[str, Any]:
        return extract_video_captions(video_bytes, filename, with_scenes=with_scenes)
