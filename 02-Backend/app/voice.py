import os
import io
import asyncio
import openai
from typing import AsyncGenerator


class VoiceService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    def speech_to_text(self, audio_file: bytes, filename: str = "audio.wav") -> str:
        audio_file_obj = io.BytesIO(audio_file)
        audio_file_obj.name = filename
        transcript = self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file_obj
        )
        return transcript.text

    def text_to_speech(self, text: str, voice: str = "alloy") -> bytes:
        response = self.client.audio.speech.create(model="tts-1", voice=voice, input=text)
        return response.content

    async def transcribe_realtime(self, audio_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[str, None]:
        buffer = bytearray()
        async for chunk in audio_stream:
            buffer.extend(chunk)
            if len(buffer) > 4096:
                text = await asyncio.to_thread(self.speech_to_text, bytes(buffer), "realtime_chunk.wav")
                buffer.clear()
                if text:
                    yield text
