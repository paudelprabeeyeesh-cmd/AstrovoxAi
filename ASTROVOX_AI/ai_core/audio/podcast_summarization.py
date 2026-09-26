import os
import re
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


class PodcastSummarizer:
    def __init__(self, use_openai: bool = True):
        self.use_openai = use_openai
        self.summaries: Dict[str, Dict[str, Any]] = {}

    def summarize(self, audio_path: str, max_summary_length: int = 500, include_transcript: bool = True) -> Dict[str, Any]:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        transcript = self._transcribe(audio_path)
        if not transcript.get("text"):
            return {"error": "Transcription returned empty text", "status": "failed"}
        summary = self._summarize_text(transcript["text"], max_summary_length)
        key_points = self._extract_key_points(transcript["text"])
        result = {
            "audio_path": audio_path,
            "transcript": transcript["text"] if include_transcript else None,
            "segments": transcript.get("segments", []) if include_transcript else None,
            "summary": summary,
            "key_points": key_points,
            "duration_estimate": self._estimate_duration(transcript.get("segments", [])),
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        summary_id = str(uuid.uuid4())
        self.summaries[summary_id] = result
        result["id"] = summary_id
        return result

    def summarize_youtube(self, youtube_url: str, max_summary_length: int = 500) -> Dict[str, Any]:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            video_id = self._extract_youtube_id(youtube_url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join(entry["text"] for entry in transcript_list)
            summary = self._summarize_text(transcript_text, max_summary_length)
            key_points = self._extract_key_points(transcript_text)
            result = {
                "source": "youtube",
                "url": youtube_url,
                "video_id": video_id,
                "transcript": transcript_text,
                "summary": summary,
                "key_points": key_points,
                "status": "completed",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            summary_id = str(uuid.uuid4())
            self.summaries[summary_id] = result
            result["id"] = summary_id
            return result
        except Exception as exc:
            logger.error(f"YouTube summarization failed: {exc}")
            return {"error": str(exc), "status": "failed", "source": "youtube"}

    def batch_summarize(self, audio_paths: List[str], max_summary_length: int = 500) -> List[Dict[str, Any]]:
        results = []
        for path in audio_paths:
            try:
                result = self.summarize(path, max_summary_length)
                results.append(result)
            except Exception as exc:
                logger.error(f"Batch summarization failed for {path}: {exc}")
                results.append({"audio_path": path, "error": str(exc), "status": "failed"})
        return results

    def _transcribe(self, audio_path: str) -> Dict[str, Any]:
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            return {"text": result.get("text", ""), "segments": result.get("segments", [])}
        except Exception as exc:
            logger.warning(f"Whisper transcription failed: {exc}")
            return {"text": "", "segments": []}

    def _summarize_text(self, text: str, max_length: int) -> str:
        if not text:
            return ""
        if self.use_openai:
            try:
                import openai
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f"Summarize the following podcast transcript in under {max_length} characters. Preserve key insights and speaker nuances."},
                        {"role": "user", "content": text[:12000]},
                    ],
                    max_tokens=max_length // 2,
                )
                return response.choices[0].message.content.strip()
            except Exception as exc:
                logger.warning(f"OpenAI summarization failed, using extractive fallback: {exc}")
        sentences = re.split(r'(?<=[.!?])\s+', text)
        summary = " ".join(sentences[: min(max(5, max_length // 50), len(sentences))])
        return summary[:max_length]

    def _extract_key_points(self, text: str, num_points: int = 5) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if not sentences:
            return []
        scored = sorted(sentences, key=lambda s: len(s.split()), reverse=True)
        return scored[:num_points]

    def _estimate_duration(self, segments: List[Dict[str, Any]]) -> Optional[float]:
        if not segments:
            return None
        return round(segments[-1].get("end", 0), 2)

    def _extract_youtube_id(self, url: str) -> Optional[str]:
        patterns = [r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", r"youtu\.be\/([0-9A-Za-z_-]{11})"]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
