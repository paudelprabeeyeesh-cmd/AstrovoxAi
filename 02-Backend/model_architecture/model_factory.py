from .transformer_block import TransformerBlock


def create_transformer_block(d_model, num_heads, d_ff=None):
    return TransformerBlock(d_model, num_heads, d_ff)


def create_transformer(d_model, num_heads, d_ff=None, num_layers=1):
    return [TransformerBlock(d_model, num_heads, d_ff) for _ in range(num_layers)]
