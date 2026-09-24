from model_architecture.model_factory import create_transformer_block, create_transformer
from model_architecture.transformer_block import TransformerBlock


class TestModelFactory:
    def test_create_transformer_block(self):
        block = create_transformer_block(d_model=32, num_heads=4)
        assert isinstance(block, TransformerBlock)

    def test_create_transformer(self):
        layers = create_transformer(d_model=32, num_heads=4, num_layers=3)
        assert len(layers) == 3
        assert all(isinstance(l, TransformerBlock) for l in layers)
