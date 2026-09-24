import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple


@dataclass
class AudioFeatures:
    waveform: np.ndarray
    sample_rate: int
    mfcc: np.ndarray
    spectrogram: np.ndarray
    duration: float


class AudioLanguageModel:
    def __init__(self, sample_rate: int = 16000, n_mfcc: int = 13):
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self._rng = np.random.default_rng(42)

    def load_audio(self, waveform: np.ndarray, sample_rate: int) -> AudioFeatures:
        if sample_rate != self.sample_rate:
            waveform = self._resample(waveform, sample_rate, self.sample_rate)
        waveform = self._normalize(waveform)
        spectrogram = self._compute_spectrogram(waveform)
        mfcc = self._compute_mfcc(spectrogram)
        duration = len(waveform) / self.sample_rate
        return AudioFeatures(
            waveform=waveform,
            sample_rate=self.sample_rate,
            mfcc=mfcc,
            spectrogram=spectrogram,
            duration=duration,
        )

    def _resample(self, signal: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        ratio = target_sr / orig_sr
        new_len = int(len(signal) * ratio)
        indices = np.linspace(0, len(signal) - 1, new_len)
        return np.interp(indices, np.arange(len(signal)), signal).astype(np.float64)

    def _normalize(self, waveform: np.ndarray) -> np.ndarray:
        max_val = np.max(np.abs(waveform))
        if max_val > 0:
            waveform = waveform / max_val
        return waveform

    def _compute_spectrogram(self, waveform: np.ndarray, frame_length: int = 400, hop_length: int = 160) -> np.ndarray:
        n_frames = 1 + (len(waveform) - frame_length) // hop_length
        spectrogram = []
        for i in range(n_frames):
            frame = waveform[i * hop_length:i * hop_length + frame_length]
            if len(frame) < frame_length:
                frame = np.pad(frame, (0, frame_length - len(frame)))
            windowed = frame * np.hanning(frame_length)
            fft = np.fft.rfft(windowed)
            mag = np.abs(fft)
            spectrogram.append(mag)
        return np.array(spectrogram, dtype=np.float64).T

    def _compute_mfcc(self, spectrogram: np.ndarray, n_mels: int = 40) -> np.ndarray:
        n_fft_bins = spectrogram.shape[0]
        mel_basis = self._mel_filterbank(n_fft_bins, n_mels)
        mel_spec = mel_basis @ spectrogram
        log_mel = np.log(mel_spec + 1e-10)
        mfcc = np.array([self._dct(frame, self.n_mfcc) for frame in log_mel.T]).T
        return mfcc

    def _mel_filterbank(self, n_fft: int, n_mels: int) -> np.ndarray:
        hz_to_mel = lambda hz: 2595 * np.log10(1 + hz / 700)
        mel_to_hz = lambda mel: 700 * (10 ** (mel / 2595) - 1)
        mel_min = hz_to_mel(0)
        mel_max = hz_to_mel(self.sample_rate / 2)
        mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
        hz_points = mel_to_hz(mel_points)
        bin_points = np.floor((self.sample_rate + 1) * hz_points / self.sample_rate / 2).astype(int)
        filterbank = np.zeros((n_mels, n_fft))
        for i in range(1, n_mels + 1):
            for j in range(n_fft):
                if bin_points[i - 1] <= j < bin_points[i]:
                    filterbank[i - 1, j] = (j - bin_points[i - 1]) / (bin_points[i] - bin_points[i - 1])
                elif bin_points[i] <= j <= bin_points[i + 1]:
                    filterbank[i - 1, j] = (bin_points[i + 1] - j) / (bin_points[i + 1] - bin_points[i])
        return filterbank

    def _dct(self, x: np.ndarray, k: int) -> np.ndarray:
        n = len(x)
        dct_coeffs = np.zeros(k)
        for i in range(k):
            sum_val = 0.0
            for j in range(n):
                sum_val += x[j] * np.cos(np.pi * i * (2 * j + 1) / (2 * n))
            dct_coeffs[i] = sum_val * np.sqrt(2 / n) if i > 0 else sum_val / np.sqrt(n)
        return dct_coeffs

    def transcribe(self, audio_features: AudioFeatures) -> str:
        energy = np.mean(np.abs(audio_features.waveform))
        mfcc_mean = audio_features.mfcc.mean(axis=1)
        if energy < 0.01:
            return "[silence]"
        text = self._greedy_decode(audio_features.mfcc)
        return text

    def _greedy_decode(self, mfcc: np.ndarray) -> str:
        words = ["hello", "world", "speech", "recognition", "audio", "test", "model", "data", "sound", "voice"]
        scores = []
        for word in words:
            word_emb = self._text_to_mfcc_embedding(word)
            sim = np.dot(mfcc.mean(axis=1), word_emb)
            scores.append(sim)
        best_idx = int(np.argmax(scores))
        return words[best_idx]

    def _text_to_mfcc_embedding(self, text: str) -> np.ndarray:
        vec = np.zeros(self.n_mfcc)
        for i, ch in enumerate(text):
            vec[i % self.n_mfcc] += ord(ch) / 255.0
        return vec / (np.linalg.norm(vec) + 1e-8)

    def answer_audio_question(self, audio_features: AudioFeatures, question: str) -> Dict[str, Any]:
        transcription = self.transcribe(audio_features)
        q_emb = self._text_to_mfcc_embedding(question)
        a_emb = self._text_to_mfcc_embedding(transcription)
        similarity = float(np.dot(q_emb, a_emb))
        answer = self._generate_audio_answer(transcription, question, audio_features)
        return {
            "transcription": transcription,
            "answer": answer,
            "similarity": similarity,
            "duration": audio_features.duration,
        }

    def _generate_audio_answer(self, transcription: str, question: str, audio_features: AudioFeatures) -> str:
        q_lower = question.lower()
        if "what" in q_lower and "say" in q_lower:
            return f"The audio says: {transcription}"
        if "how long" in q_lower:
            return f"The audio duration is {audio_features.duration:.2f} seconds."
        if "loud" in q_lower or "quiet" in q_lower:
            rms = np.sqrt(np.mean(audio_features.waveform ** 2))
            return "The audio is loud." if rms > 0.3 else "The audio is quiet."
        return f"Audio analysis complete. Transcribed text: {transcription}"

    def compute_snr(self, clean: np.ndarray, noisy: np.ndarray) -> float:
        signal_power = np.mean(clean ** 2)
        noise_power = np.mean((clean - noisy) ** 2)
        if noise_power == 0:
            return float("inf")
        return 10 * np.log10(signal_power / noise_power)

    def compute_pesq_like(self, clean: np.ndarray, degraded: np.ndarray) -> float:
        snr = self.compute_snr(clean, degraded)
        return max(1.0, min(4.5, 1.0 + snr / 10.0))
