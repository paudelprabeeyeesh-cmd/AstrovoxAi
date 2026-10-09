import numpy as np
import pytest
from ..vision_patch_encoder import VisionPatchEncoder


class TestVisionPatchEncoder:
    def test_output_shape(self):
        B, H, W, C = 2, 56, 56, 3
        model = VisionPatchEncoder(image_size=H, patch_size=14, d_model=64)
        images = np.random.randn(B, H, W, C)
        out = model.forward(images)
        assert out.shape == (B, (H // 14) ** 2, 64)

    def test_invalid_image_size(self):
        with pytest.raises(AssertionError):
            VisionPatchEncoder(image_size=50, patch_size=14, d_model=64)
