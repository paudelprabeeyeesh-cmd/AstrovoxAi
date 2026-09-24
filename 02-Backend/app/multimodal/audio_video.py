"""
Multimodal extraction - audio and video processing.

Modules:
- Audio transcription via Whisper
- Video caption extraction via Whisper + ffmpeg
"""

from typing import Optional


class AudioExtractor:
    """Extract text from audio files."""

    @staticmethod
    def transcribe(file_path: str, model: str = "base") -> str:
        from app.parsers.document_parsers import DocumentParsers
        return DocumentParsers.parse_audio(file_path, model=model)


class VideoExtractor:
    """Extract captions from video files."""

    @staticmethod
    def extract_captions(file_path: str) -> str:
        from app.parsers.document_parsers import DocumentParsers
        return DocumentParsers.parse_video(file_path)
