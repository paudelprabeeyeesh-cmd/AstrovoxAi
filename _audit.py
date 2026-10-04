"""Audit: check which items from the specification are actually implemented."""

import importlib

# (phase, item, module to look in, symbol that would prove it exists)
SPEC = [
    # Phase 1 - tensor engine
    ("1", "Tensor class", "astrovox.tensor.tensor", "Tensor"),
    ("1", "Storage", "astrovox.tensor.storage", "Storage"),
    ("1", "Memory pool", "astrovox.tensor.storage", "MemoryPool"),
    ("1", "Shape system", "astrovox.tensor.shape", "Shape"),
    ("1", "Device abstraction", "astrovox.tensor.device", "Device"),
    ("1", "Backend registry", "astrovox.tensor.device", "register_backend"),
    ("1", "Serialization", "astrovox.tensor.serialization", "save_checkpoint"),
    ("1", "Advanced indexing", "astrovox.tensor.tensor", "Tensor"),
    ("1", "Index select", "astrovox.tensor.tensor", "Tensor"),
    ("1", "Narrow", "astrovox.tensor.tensor", "Tensor"),
    # Phase 2 - math
    ("2", "Add", "astrovox.ops.math", "add"),
    ("2", "Sub", "astrovox.ops.math", "sub"),
    ("2", "Mul", "astrovox.ops.math", "mul"),
    ("2", "Div", "astrovox.ops.math", "div"),
    ("2", "Pow", "astrovox.ops.math", "pow"),
    ("2", "Matmul", "astrovox.ops.math", "matmul"),
    ("2", "Dot", "astrovox.ops.math", "dot"),
    ("2", "Outer", "astrovox.ops.math", "outer"),
    ("2", "Sum", "astrovox.ops.reduction", "sum"),
    ("2", "Mean", "astrovox.ops.reduction", "mean"),
    ("2", "Max", "astrovox.ops.reduction", "max"),
    ("2", "Min", "astrovox.ops.reduction", "min"),
    ("2", "Argmax", "astrovox.ops.reduction", "argmax"),
    ("2", "Argmin", "astrovox.ops.reduction", "argmin"),
    ("2", "Var", "astrovox.ops.reduction", "var"),
    ("2", "Std", "astrovox.ops.reduction", "std"),
    ("2", "Cumsum", "astrovox.ops.reduction", "cumsum"),
    ("2", "Log", "astrovox.ops.math", "log"),
    ("2", "Exp", "astrovox.ops.math", "exp"),
    ("2", "Sqrt", "astrovox.ops.math", "sqrt"),
    ("2", "ReLU", "astrovox.ops.activation", "relu"),
    ("2", "GELU", "astrovox.ops.activation", "gelu"),
    ("2", "SiLU", "astrovox.ops.activation", "silu"),
    ("2", "Mish", "astrovox.ops.activation", "mish"),
    ("2", "Softplus", "astrovox.ops.activation", "softplus"),
    ("2", "Softmax", "astrovox.ops.activation", "softmax"),
    ("2", "LogSoftmax", "astrovox.ops.activation", "log_softmax"),
    ("2", "Sigmoid", "astrovox.ops.activation", "sigmoid"),
    ("2", "Tanh", "astrovox.ops.activation", "tanh"),
    ("2", "LeakyReLU", "astrovox.ops.activation", "leaky_relu"),
    # Phase 3 - autograd
    ("3", "Dynamic graph", "astrovox.autograd.graph", "walk_from"),
    ("3", "Engine", "astrovox.autograd.engine", "Engine"),
    ("3", "Backprop", "astrovox.autograd.engine", "backward"),
    ("3", "Grad accumulation", "astrovox.autograd.engine", "backward"),
    ("3", "Grad clipping", "astrovox.autograd.engine", "clip_grad_norm"),
    ("3", "Custom Function", "astrovox.autograd.function", "Function"),
    ("3", "Numerical check", "astrovox.autograd.gradients", "check_gradients"),
    ("3", "Graph optimization", "astrovox.autograd.graph", "topological_order"),
    # Phase 4 - nn core
    ("4", "Module", "astrovox.nn.module", "Module"),
    ("4", "Parameter", "astrovox.nn.module", "Parameter"),
    ("4", "Sequential", "astrovox.nn.module", "Sequential"),
    ("4", "ModuleList", "astrovox.nn.module", "ModuleList"),
    ("4", "Xavier", "astrovox.nn.module", "init_xavier_uniform"),
    ("4", "Kaiming", "astrovox.nn.module", "init_kaiming_uniform"),
    ("4", "Orthogonal", "astrovox.nn.module", "init_orthogonal"),
    ("4", "State dict", "astrovox.nn.module", "Module"),
    # Phase 5 - layers
    ("5", "Linear", "astrovox.nn.linear", "Linear"),
    ("5", "Embedding", "astrovox.nn.linear", "Embedding"),
    ("5", "Dropout", "astrovox.nn.linear", "Dropout"),
    ("5", "LayerNorm", "astrovox.nn.layernorm", "LayerNorm"),
    ("5", "RMSNorm", "astrovox.nn.rmsnorm", "RMSNorm"),
    ("5", "GroupNorm", "astrovox.ops.normalization", "group_norm"),
    # Phase 6/7 - losses
    ("7", "MSE", "astrovox.ops.loss", "mse_loss"),
    ("7", "MAE", "astrovox.ops.loss", "l1_loss"),
    ("7", "CrossEntropy", "astrovox.ops.loss", "cross_entropy"),
    ("7", "BCE", "astrovox.ops.loss", "bce_loss"),
    ("7", "BCEWithLogits", "astrovox.ops.loss", "binary_cross_entropy_with_logits"),
    ("7", "KL", "astrovox.ops.loss", "kl_div"),
    ("7", "Huber", "astrovox.ops.loss", "huber_loss"),
    ("7", "NLL", "astrovox.ops.loss", "nll_loss"),
    # Phase 8 - optimizers
    ("8", "SGD", "astrovox.optim.sgd", "SGD"),
    ("8", "Adam", "astrovox.optim.adam", "Adam"),
    ("8", "AdamW", "astrovox.optim.adam", "AdamW"),
    ("8", "Lion", "astrovox.optim.lion", "Lion"),
    ("8", "Cosine schedule", "astrovox.optim.scheduler", "CosineAnnealingLR"),
    ("8", "OneCycle", "astrovox.optim.scheduler", "OneCycleLR"),
    ("8", "Warmup", "astrovox.optim.scheduler", "LinearWarmupLR"),
    # Phase 10/11/12 - tokenizer + transformer + LM
    ("10", "Char tokenizer", "astrovox.nlp.tokenizer", "CharTokenizer"),
    ("10", "Word tokenizer", "astrovox.nlp.tokenizer", "WordTokenizer"),
    ("11", "MultiHeadAttention", "astrovox.nn.transformer", "MultiHeadAttention"),
    ("11", "Positional encoding", "astrovox.nn.transformer", "PositionalEncoding"),
    ("11", "TransformerEncoder", "astrovox.nn.transformer", "TransformerEncoder"),
    ("11", "TransformerBlock", "astrovox.nn.transformer", "TransformerBlock"),
    ("11", "FeedForward", "astrovox.nn.transformer", "FeedForward"),
    ("12", "LanguageModel", "astrovox.nlp.language_model", "LanguageModel"),
    ("12", "Sampling", "astrovox.nlp.language_model", "LanguageModel"),
    # Phase 15 - debugging
    ("15", "Graph inspector", "astrovox.debug.inspector", "inspect"),
    ("15", "Gradient dashboard", "astrovox.debug.diagnostics", "dashboard"),
    ("15", "Memory debugger", "astrovox.debug.diagnostics", "memory_report"),
    # Phase 16/17 - serialization + perf
    ("16", "Checkpoint", "astrovox.tensor.serialization", "load_checkpoint"),
    ("17", "FLOP counter", "astrovox.profile.profiler", "count_flops"),
    ("17", "Profiler", "astrovox.profile.profiler", "Profiler"),
    ("17", "Allocation tracker", "astrovox.profile.profiler", "AllocationTracker"),
    ("17", "Benchmark suite", "astrovox.benchmark", "full_suite"),
    # Phase 25 - hub
    ("25", "HF push", "astrovox.hub.client", "push_model"),
    ("25", "HF pull", "astrovox.hub.client", "pull_model"),
    ("25", "Model card", "astrovox.hub.card", "build_card"),
]

missing = []
present = 0
for phase, item, module_name, symbol in SPEC:
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, symbol):
            present += 1
        else:
            missing.append((phase, item, module_name, symbol))
    except ImportError as exc:
        missing.append((phase, item, module_name, f"IMPORT FAILED: {exc}"))

print(f"present: {present}/{len(SPEC)}")
if missing:
    print("missing:")
    for phase, item, module_name, symbol in missing:
        print(f"  phase {phase:>2}  {item:<24} -> {module_name}.{symbol}")

# Now probe for things that should exist but may not, by name alone.
PROBES = [
    ("Conv2d", ["astrovox.nn.conv", "Conv2d"]),
    ("Conv1d", ["astrovox.nn.conv", "Conv1d"]),
    ("MaxPool", ["astrovox.nn.pool", "MaxPool"]),
    ("BatchNorm", ["astrovox.nn.norm", "BatchNorm"]),
    ("BPE", ["astrovox.nlp.bpe", "BPETokenizer"]),
    ("RoPE", ["astrovox.nn.transformer", "RotaryEmbedding"]),
    ("KV cache", ["astrovox.nn.transformer", "KVCache"]),
    ("DataLoader", ["astrovox.data.loader", "DataLoader"]),
    ("Dataset", ["astrovox.data.dataset", "Dataset"]),
    ("Beam search", ["astrovox.nlp.decode", "beam_search"]),
    ("EarlyStopping", ["astrovox.training.callbacks", "EarlyStopping"]),
    ("EMA", ["astrovox.training.ema", "EMA"]),
    ("Gradient checkpoint", ["astrovox.autograd.checkpoint", "checkpoint"]),
    ("Metrics", ["astrovox.metrics", "accuracy"]),
    ("RMSProp", ["astrovox.optim.rmsprop", "RMSProp"]),
    ("AdaGrad", ["astrovox.optim.adagrad", "AdaGrad"]),
    ("LAMB", ["astrovox.optim.lamb", "LAMB"]),
    ("Focal loss", ["astrovox.ops.loss", "focal_loss"]),
    ("Triplet loss", ["astrovox.ops.loss", "triplet_loss"]),
    ("Dice loss", ["astrovox.ops.loss", "dice_loss"]),
    ("Fourier FFT", ["astrovox.ops.linalg", "fft"]),
    ("SVD", ["astrovox.ops.linalg", "svd"]),
    ("Quantize", ["astrovox.ops.quantization", "quantize"]),
    ("Sparse tensor", ["astrovox.tensor.sparse", "SparseTensor"]),
    ("Plugin loader", ["astrovox.plugins", "PluginRegistry"]),
    ("Vector index", ["astrovox.vector.index", "HNSWIndex"]),
]

print()
print("absent probes (expected for anything not built yet):")
found_any = 0
for label, (module_name, symbol) in PROBES:
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, symbol):
            print(f"  PRESENT  {label} -> {module_name}.{symbol}")
            found_any += 1
    except ImportError:
        pass
if not found_any:
    print("  (none of the probed extension modules exist)")
