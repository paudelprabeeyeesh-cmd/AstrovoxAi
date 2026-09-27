import math


def count_parameters(hidden_size, vocab_size, num_hidden_layers, num_attention_heads, intermediate_size, max_position_embeddings):
    head_dim = hidden_size // num_attention_heads
    params = 0
    params += vocab_size * hidden_size
    params += max_position_embeddings * hidden_size
    per_block = 0
    per_block += 2 * hidden_size
    per_block += 4 * hidden_size * hidden_size
    per_block += 2 * hidden_size
    per_block += hidden_size * intermediate_size + intermediate_size * hidden_size
    params += num_hidden_layers * per_block
    params += 2 * hidden_size
    params += hidden_size * vocab_size
    return params


def memory_estimation(num_params, dtype_bytes=2, training=True):
    weights_mem = num_params * dtype_bytes
    grad_mem = weights_mem if training else 0
    optimizer_mem = weights_mem * 2 if training else 0
    base_mem = weights_mem + grad_mem + optimizer_mem
    return {
        "weights_gb": weights_mem / (1024 ** 3),
        "gradients_gb": grad_mem / (1024 ** 3),
        "optimizer_gb": optimizer_mem / (1024 ** 3),
        "total_base_gb": base_mem / (1024 ** 3),
    }


def chinchilla_optimal_tokens(num_params):
    return 20 * num_params


def estimate_training_time(num_params, tokens_per_second, optimal_tokens=None):
    if optimal_tokens is None:
        optimal_tokens = chinchilla_optimal_tokens(num_params)
    steps = optimal_tokens / 2048
    seconds = steps / tokens_per_second
    days = seconds / 86400
    return {"steps": int(steps), "seconds": seconds, "days": days}
