import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple


@dataclass
class EvaluationResult:
    metric_name: str
    score: float
    details: Dict[str, Any] = field(default_factory=dict)


class VQAMetrics:
    def __init__(self):
        pass

    def exact_match(self, prediction: str, ground_truth: str) -> float:
        return 1.0 if prediction.strip().lower() == ground_truth.strip().lower() else 0.0

    def f1_score(self, prediction: str, ground_truth: str) -> float:
        pred_tokens = set(prediction.lower().split())
        gt_tokens = set(ground_truth.lower().split())
        if not pred_tokens and not gt_tokens:
            return 1.0
        if not pred_tokens or not gt_tokens:
            return 0.0
        intersection = pred_tokens & gt_tokens
        precision = len(intersection) / len(pred_tokens)
        recall = len(intersection) / len(gt_tokens)
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def vqa_accuracy(self, predictions: List[str], ground_truths: List[str], min_occurrences: int = 3) -> float:
        if len(predictions) != len(ground_truths):
            raise ValueError("Predictions and ground truths must have the same length")
        if not predictions:
            return 0.0
        scores = []
        for pred, gt in zip(predictions, ground_truths):
            gt_tokens = gt.lower().split()
            pred_tokens = pred.lower().split()
            if not gt_tokens:
                scores.append(0.0)
                continue
            gt_counter = {}
            for token in gt_tokens:
                gt_counter[token] = gt_counter.get(token, 0) + 1
            acc = 0.0
            for token in pred_tokens:
                if token in gt_counter and gt_counter[token] > 0:
                    acc += 1
                    gt_counter[token] -= 1
            acc = min(acc / min_occurrences, 1.0)
            scores.append(acc)
        return float(np.mean(scores))

    def bleu_like(self, prediction: str, reference: str, max_n: int = 4) -> float:
        pred_tokens = prediction.lower().split()
        ref_tokens = reference.lower().split()
        if not pred_tokens or not ref_tokens:
            return 0.0
        max_n = min(max_n, min(len(pred_tokens), len(ref_tokens)))
        if max_n == 0:
            return 0.0
        scores = []
        for n in range(1, max_n + 1):
            pred_ngrams = [tuple(pred_tokens[i:i + n]) for i in range(len(pred_tokens) - n + 1)]
            ref_ngrams = [tuple(ref_tokens[i:i + n]) for i in range(len(ref_tokens) - n + 1)]
            if not pred_ngrams:
                scores.append(0.0)
                continue
            ref_counter = {}
            for ng in ref_ngrams:
                ref_counter[ng] = ref_counter.get(ng, 0) + 1
            matches = 0
            for ng in pred_ngrams:
                if ng in ref_counter and ref_counter[ng] > 0:
                    matches += 1
                    ref_counter[ng] -= 1
            scores.append(matches / len(pred_ngrams))
        if not scores or min(scores) == 0:
            return 0.0
        return float(np.exp(np.mean(np.log(np.array(scores) + 1e-10))))


class AudioMetrics:
    def __init__(self):
        pass

    def snr(self, clean: np.ndarray, noisy: np.ndarray) -> float:
        signal_power = np.mean(clean ** 2)
        noise_power = np.mean((clean - noisy) ** 2)
        if noise_power == 0:
            return float("inf")
        return 10 * np.log10(signal_power / noise_power)

    def psd_ratio(self, clean: np.ndarray, processed: np.ndarray) -> float:
        clean_psd = np.abs(np.fft.rfft(clean)) ** 2
        proc_psd = np.abs(np.fft.rfft(processed)) ** 2
        ratio = np.mean(proc_psd / (clean_psd + 1e-10))
        return float(np.clip(ratio, 0, 10))

    def stoi_like(self, clean: np.ndarray, processed: np.ndarray, sample_rate: int = 16000) -> float:
        frame_length = 256
        hop_length = 128
        num_frames = 1 + (len(clean) - frame_length) // hop_length
        correlations = []
        for i in range(num_frames):
            start = i * hop_length
            c_frame = clean[start:start + frame_length]
            p_frame = processed[start:start + frame_length]
            if len(c_frame) < frame_length or len(p_frame) < frame_length:
                continue
            c_fft = np.fft.rfft(c_frame * np.hanning(frame_length))
            p_fft = np.fft.rfft(p_frame * np.hanning(frame_length))
            corr = np.corrcoef(np.abs(c_fft), np.abs(p_fft))[0, 1]
            if not np.isnan(corr):
                correlations.append(corr)
        if not correlations:
            return 0.0
        return float(np.clip(np.mean(correlations), 0, 1))


class VideoMetrics:
    def __init__(self):
        pass

    def psnr(self, original: np.ndarray, reconstructed: np.ndarray) -> float:
        mse = np.mean((original - reconstructed) ** 2)
        if mse == 0:
            return float("inf")
        max_val = 255.0
        return 20 * np.log10(max_val / np.sqrt(mse))

    def ssim(self, original: np.ndarray, reconstructed: np.ndarray, window_size: int = 11) -> float:
        if original.ndim == 3:
            original = original.mean(axis=2)
            reconstructed = reconstructed.mean(axis=2)
        h, w = original.shape
        win = self._fspecial(window_size, 1.5)
        mu1 = self._filter2d(original, win)
        mu2 = self._filter2d(reconstructed, win)
        sigma1_sq = self._filter2d(original ** 2, win) - mu1 ** 2
        sigma2_sq = self._filter2d(reconstructed ** 2, win) - mu2 ** 2
        sigma12 = self._filter2d(original * reconstructed, win) - mu1 * mu2
        c1 = 0.01 ** 2
        c2 = 0.03 ** 2
        numerator = (2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)
        denominator = (mu1 ** 2 + mu2 ** 2 + c1) * (sigma1_sq + sigma2_sq + c2)
        ssim_map = numerator / (denominator + 1e-8)
        return float(np.mean(ssim_map))

    def _fspecial(self, size: int, sigma: float) -> np.ndarray:
        x = np.arange(size) - size // 2
        y = x[:, None]
        g = np.exp(-(x ** 2 + y ** 2) / (2 * sigma ** 2))
        return g / g.sum()

    def _filter2d(self, img: np.ndarray, win: np.ndarray) -> np.ndarray:
        return self._convolve2d(img, win)

    def _convolve2d(self, image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        kh, kw = kernel.shape
        h, w = image.shape
        output = np.zeros_like(image)
        for i in range(kh // 2, h - kh // 2):
            for j in range(kw // 2, w - kw // 2):
                output[i, j] = np.sum(image[i - kh // 2:i + kh // 2 + 1, j - kw // 2:j + kw // 2 + 1] * kernel)
        return output

    def temporal_consistency(self, frames: np.ndarray) -> float:
        if frames.shape[0] < 2:
            return 1.0
        diffs = []
        for i in range(frames.shape[0] - 1):
            frame_a = frames[i].mean(axis=2) if frames[i].ndim == 3 else frames[i]
            frame_b = frames[i + 1].mean(axis=2) if frames[i + 1].ndim == 3 else frames[i + 1]
            if frame_a.shape != frame_b.shape:
                continue
            diff = np.mean((frame_a - frame_b) ** 2)
            diffs.append(diff)
        if not diffs:
            return 1.0
        avg_diff = np.mean(diffs)
        if avg_diff < 1e-6:
            return 1.0
        return float(np.clip(1.0 - avg_diff / 255.0, 0, 1))


class MultimodalEvaluator:
    def __init__(self):
        self.vqa_metrics = VQAMetrics()
        self.audio_metrics = AudioMetrics()
        self.video_metrics = VideoMetrics()

    def evaluate_vqa(self, predictions: List[str], ground_truths: List[str]) -> Dict[str, EvaluationResult]:
        exact = [self.vqa_metrics.exact_match(p, g) for p, g in zip(predictions, ground_truths)]
        f1 = [self.vqa_metrics.f1_score(p, g) for p, g in zip(predictions, ground_truths)]
        acc = self.vqa_metrics.vqa_accuracy(predictions, ground_truths)
        return {
            "exact_match": EvaluationResult("exact_match", float(np.mean(exact))),
            "f1_score": EvaluationResult("f1_score", float(np.mean(f1))),
            "vqa_accuracy": EvaluationResult("vqa_accuracy", acc),
        }

    def evaluate_audio(self, clean_signals: List[np.ndarray], processed_signals: List[np.ndarray]) -> Dict[str, EvaluationResult]:
        snrs = [self.audio_metrics.snr(c, p) for c, p in zip(clean_signals, processed_signals)]
        stois = [self.audio_metrics.stoi_like(c, p) for c, p in zip(clean_signals, processed_signals)]
        return {
            "snr": EvaluationResult("snr", float(np.mean(snrs))),
            "stoi_like": EvaluationResult("stoi_like", float(np.mean(stois))),
        }

    def evaluate_video(self, original_frames: np.ndarray, reconstructed_frames: np.ndarray) -> Dict[str, EvaluationResult]:
        psnrs = []
        ssims = []
        for i in range(min(original_frames.shape[0], reconstructed_frames.shape[0])):
            psnrs.append(self.video_metrics.psnr(original_frames[i], reconstructed_frames[i]))
            ssims.append(self.video_metrics.ssim(original_frames[i], reconstructed_frames[i]))
        temporal = self.video_metrics.temporal_consistency(reconstructed_frames)
        return {
            "psnr": EvaluationResult("psnr", float(np.mean(psnrs)) if psnrs else 0.0),
            "ssim": EvaluationResult("ssim", float(np.mean(ssims)) if ssims else 0.0),
            "temporal_consistency": EvaluationResult("temporal_consistency", temporal),
        }
