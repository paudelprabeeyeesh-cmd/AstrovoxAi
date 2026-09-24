import numpy as np
from ..audio_codec_encoder import AudioCodecEncoder, mel_spectrogram_to_log


class TestAudioCodecEncoder:
    def test_encode_output_shape(self):
        encoder = AudioCodecEncoder(n_codebooks=4, codebook_size=8, d_model=16)
        mel = np.random.randn(2, 10, 16)
        tokens = encoder.encode(mel)
        assert tokens.shape == (2, 10, 4)

    def test_decode_output_shape(self):
        encoder = AudioCodecEncoder(n_codebooks=4, codebook_size=8, d_model=16)
        tokens = np.random.randint(0, 8, size=(2, 10, 4))
        recon = encoder.decode(tokens)
        assert recon.shape == (2, 10, 16)

    def test_mel_shape(self):
        audio = np.random.randn(16000)
        mel = mel_spectrogram_to_log(audio, sr=16000)
        assert mel.shape[0] == 80
