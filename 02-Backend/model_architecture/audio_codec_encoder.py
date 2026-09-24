import numpy as np


def mel_spectrogram_to_log(audio, sr, n_fft=1024, hop_length=256, n_mels=80):
    stft = np.array([np.fft.rfft(audio[i:i + n_fft]) for i in range(0, len(audio) - n_fft + 1, hop_length)])
    mag = np.abs(stft)
    mel_basis = np.random.randn(n_mels, mag.shape[1])
    mel = mel_basis @ mag.T
    return np.log(mel + 1e-5)


def vector_quantize(x, codebook):
    x_exp = x[..., None, :]
    cb_exp = codebook[None, :]
    dists = np.sum((x_exp - cb_exp) ** 2, axis=-1)
    idx = np.argmin(dists, axis=-1)
    return codebook[idx], idx


class AudioCodecEncoder:
    def __init__(self, n_codebooks=4, codebook_size=256, d_model=128):
        self.n_codebooks = n_codebooks
        self.codebook_size = codebook_size
        self.d_model = d_model
        self.codebooks = [np.random.randn(codebook_size, d_model) * 0.02 for _ in range(n_codebooks)]

    def encode(self, mel):
        residual = mel
        tokens = []
        for cb in self.codebooks:
            z, idx = vector_quantize(residual, cb)
            tokens.append(idx)
            residual = residual - z
        return np.stack(tokens, axis=-1)

    def decode(self, tokens):
        B, T, K = tokens.shape
        recon = np.zeros((B, T, self.d_model))
        for k in range(K):
            cb = self.codebooks[k]
            recon += cb[tokens[:, :, k]]
        return recon
