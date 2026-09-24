import numpy as np


class VisionPatchEncoder:
    def __init__(self, image_size, patch_size, d_model):
        assert image_size % patch_size == 0
        self.patch_size = patch_size
        self.num_patches = (image_size // patch_size) ** 2
        self.d_model = d_model
        self.proj = np.random.randn(patch_size * patch_size * 3, d_model) * 0.02
        self.pos_emb = np.random.randn(self.num_patches, d_model) * 0.02

    def forward(self, images):
        B = images.shape[0]
        p = self.patch_size
        patches = images.reshape(B, -1, p * p * 3)
        projected = patches @ self.proj
        return projected + self.pos_emb[None, :, :]
