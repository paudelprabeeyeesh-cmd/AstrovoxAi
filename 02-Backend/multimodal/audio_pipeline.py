from dataclasses import dataclass, field
from math import cos, log, log10, pi, sqrt
from typing import Any, Dict, List, Optional


@dataclass
class AudioFeatures:
    waveform: List[float]
    sample_rate: int
    mfcc: List[List[float]]
    spectrogram: List[List[float]]
    duration: float


@dataclass
class AudioPipelineResult:
    features: AudioFeatures
    transcription: str
    snr: float
    pesq: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class AudioPipeline:
    def __init__(self, sample_rate: int = 16000, n_mfcc: int = 13):
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc

    def _to_list(self, obj):
        if hasattr(obj, "tolist"):
            return obj.tolist()
        if isinstance(obj, list):
            return obj
        return list(obj)

    def process(self, waveform, sample_rate: int) -> AudioPipelineResult:
        waveform = self._to_list(waveform)
        feats = self.load_audio(waveform, sample_rate)
        transcription = self.transcribe(feats)
        snr = self.compute_snr(feats.waveform, feats.waveform)
        pesq = self.compute_pesq_like(feats.waveform, feats.waveform)
        return AudioPipelineResult(
            features=feats,
            transcription=transcription,
            snr=snr,
            pesq=pesq,
            metadata={
                "sample_rate": feats.sample_rate,
                "duration": feats.duration,
            },
        )

    def load_audio(self, waveform: List[float], sample_rate: int) -> AudioFeatures:
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

    def _resample(self, signal: List[float], orig_sr: int, target_sr: int) -> List[float]:
        ratio = target_sr / orig_sr
        new_len = int(len(signal) * ratio)
        return [signal[int(i / ratio)] for i in range(new_len)]

    def _normalize(self, waveform: List[float]) -> List[float]:
        max_val = max(abs(x) for x in waveform)
        if max_val > 0:
            return [x / max_val for x in waveform]
        return list(waveform)

    def _window(self, n: int) -> List[float]:
        return [0.5 * (1 - cos(2 * pi * i / (n - 1))) for i in range(n)]

    def _compute_spectrogram(
        self, waveform: List[float], frame_length: int = 400, hop_length: int = 160
    ) -> List[List[float]]:
        n_frames = 1 + (len(waveform) - frame_length) // hop_length
        win = self._window(frame_length)
        spectrogram = []
        for i in range(n_frames):
            frame = waveform[i * hop_length : i * hop_length + frame_length]
            if len(frame) < frame_length:
                frame = frame + [0.0] * (frame_length - len(frame))
            windowed = [frame[j] * win[j] for j in range(frame_length)]
            fft = self._fft(windowed)
            mag = [abs(f) for f in fft[: frame_length // 2 + 1]]
            spectrogram.append(mag)
        return spectrogram

    def _fft(self, x: List[float]) -> List[complex]:
        n = len(x)
        if n == 1:
            return [complex(x[0], 0)]
        even = self._fft(x[0::2])
        odd = self._fft(x[1::2])
        combined = [0] * n
        for k in range(n // 2):
            t = complex(cos(-2 * pi * k / n), sin(-2 * pi * k / n)) * odd[k]
            combined[k] = even[k] + t
            combined[k + n // 2] = even[k] - t
        return combined

    def _compute_mfcc(self, spectrogram: List[List[float]], n_mels: int = 40) -> List[List[float]]:
        n_fft_bins = len(spectrogram[0]) if spectrogram else 0
        mel_basis = self._mel_filterbank(n_fft_bins, n_mels)
        mfcc = []
        for frame in spectrogram:
            mel_spec = [sum(mel_basis[m][b] * frame[b] for b in range(n_fft_bins)) for m in range(n_mels)]
            log_mel = [log(max(s, 1e-10)) for s in mel_spec]
            mfcc.append(self._dct(log_mel, self.n_mfcc))
        return mfcc

    def _mel_filterbank(self, n_fft: int, n_mels: int) -> List[List[float]]:
        def hz_to_mel(hz):
            return 2595 * log10(1 + hz / 700)

        def mel_to_hz(mel):
            return 700 * (10 ** (mel / 2595) - 1)

        mel_min = hz_to_mel(0)
        mel_max = hz_to_mel(self.sample_rate / 2)
        mel_points = [mel_min + i * (mel_max - mel_min) / (n_mels + 2) for i in range(n_mels + 2)]
        hz_points = [mel_to_hz(m) for m in mel_points]
        bin_points = [int((self.sample_rate + 1) * h / self.sample_rate / 2) for h in hz_points]
        filterbank = [[0.0] * n_fft for _ in range(n_mels)]
        for i in range(1, n_mels + 1):
            for j in range(n_fft):
                if bin_points[i - 1] <= j < bin_points[i]:
                    filterbank[i - 1][j] = (j - bin_points[i - 1]) / (bin_points[i] - bin_points[i - 1])
                elif bin_points[i] <= j <= bin_points[i + 1]:
                    filterbank[i - 1][j] = (bin_points[i + 1] - j) / (bin_points[i + 1] - bin_points[i])
        return filterbank

    def _dct(self, x: List[float], k: int) -> List[float]:
        n = len(x)
        dct_coeffs = []
        for i in range(k):
            s = 0.0
            for j in range(n):
                s += x[j] * cos(pi * i * (2 * j + 1) / (2 * n))
            coeff = s * sqrt(2 / n) if i > 0 else s / sqrt(n)
            dct_coeffs.append(coeff)
        return dct_coeffs

    def _text_to_mfcc_embedding(self, text: str) -> List[float]:
        vec = [0.0] * self.n_mfcc
        for i, ch in enumerate(text):
            vec[i % self.n_mfcc] += ord(ch) / 255.0
        norm = sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def _greedy_decode(self, mfcc: List[List[float]]) -> str:
        words = ["hello", "world", "speech", "recognition", "audio", "test", "model", "data", "sound", "voice"]
        n_frames = len(mfcc)
        n_coeffs = len(mfcc[0]) if mfcc else 0
        mean_mfcc = [sum(mfcc[f][c] for f in range(n_frames)) / n_frames for c in range(n_coeffs)]
        scores = []
        for word in words:
            emb = self._text_to_mfcc_embedding(word)
            scores.append(sum(mean_mfcc[i] * emb[i] for i in range(n_coeffs)))
        best = scores.index(max(scores))
        return words[best]

    def transcribe(self, features: AudioFeatures) -> str:
        energy = sum(abs(x) for x in features.waveform) / len(features.waveform)
        if energy < 0.01:
            return "[silence]"
        return self._greedy_decode(features.mfcc)

    def compute_snr(self, clean: List[float], noisy: List[float]) -> float:
        signal_power = sum(x * x for x in clean) / len(clean)
        noise_power = sum((clean[i] - noisy[i]) ** 2 for i in range(len(clean))) / len(clean)
        if noise_power == 0:
            return float("inf")
        return 10 * log10(signal_power / noise_power)

    def compute_pesq_like(self, clean: List[float], degraded: List[float]) -> float:
        snr = self.compute_snr(clean, degraded)
        return max(1.0, min(4.5, 1.0 + snr / 10.0))
