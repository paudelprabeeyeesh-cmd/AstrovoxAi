from typing import Optional, Dict, Any
import torch
import torch.nn as nn


class AudioTranscriber:
    def __init__(self, model_name: str = 'whisper', device: str = 'cuda'):
        self.model_name = model_name
        self.device = device
        self.model = None
        if model_name == 'whisper':
            try:
                import whisper
                self.model = whisper.load_model('base', device=device)
            except ImportError:
                pass

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        if self.model is None:
            return {'error': 'Whisper not installed', 'text': ''}
        result = self.model.transcribe(audio_path, language=language)
        return {'text': result.get('text', ''), 'segments': result.get('segments', []), 'language': result.get('language', '')}

    def transcribe_batch(self, audio_paths: List[str]) -> List[Dict[str, Any]]:
        return [self.transcribe(path) for path in audio_paths]
