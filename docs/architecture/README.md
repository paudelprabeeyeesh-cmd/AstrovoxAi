# Architecture Diagrams

This section contains Mermaid diagrams for the AstrovoxAI model training and inference architecture.

## Model Architecture

```mermaid
graph TD
    A[Input IDs] --> B[Token Embedding]
    B --> C[Dropout]
    C --> D[Transformer Block 1]
    D --> E[Transformer Block N]
    E --> F[Final RMSNorm]
    F --> G[LM Head]
    G --> H[Logits]

    subgraph TransformerBlock
        D1[RMSNorm] --> D2[Self-Attention + RoPE]
        D2 --> D3[Residual]
        D3 --> D4[RMSNorm]
        D4 --> D5[SwiGLU MLP]
        D5 --> D6[Residual]
    end
```

## Training Pipeline

```mermaid
graph LR
    A[Raw Text] --> B[Tokenizer]
    B --> C[TextDataset]
    C --> D[DataLoader]
    D --> E[Forward Pass]
    E --> F[Loss Computation]
    F --> G[Backward Pass]
    G --> H[Gradient Clipping]
    H --> I[Optimizer Step]
    I --> J[LR Scheduler]
    J --> K[Checkpoint]
    K --> L[Validation]
    L --> M{Improving?}
    M -->|Yes| D
    M -->|No| N[Early Stop]
```

## Inference Pipeline

```mermaid
graph LR
    A[Prompt] --> B[Tokenizer]
    B --> C[Input IDs]
    C --> D[Model Forward]
    D --> E[Logits]
    E --> F[Sampling / Beam Search]
    F --> G[Next Token]
    G --> H{Stop?}
    H -->|No| D
    H -->|Yes| I[Detokenize]
    I --> J[Output Text]
```

## Quantization Flow

```mermaid
graph TD
    A[FP32 Model] --> B{Format?}
    B -->|FP16/BF16| C[Cast dtype]
    B -->|INT8| D[Calibration Data]
    D --> E[Activation Stats]
    E --> F[Compute Scales]
    F --> G[Quantize Weights]
    G --> H[QuantizedLinear]
    B -->|GPTQ/AWQ| I[External Library]
    I --> J[Quantized Model]
    C --> K[Inference]
    H --> K
    J --> K
```

## Export Formats

```mermaid
graph TD
    A[PyTorch Model] --> B{Target Format}
    B -->|HuggingFace| C[config.json + model.safetensors]
    B -->|ONNX| D[model.onnx + ORT validation]
    D --> E[TensorRT Engine]
    B -->|GGUF| F[model.gguf]
    B -->|SafeTensors| G[model.safetensors]
    C --> H[Deploy]
    E --> H
    F --> I[Ollama / llama.cpp]
    I --> H
    G --> H
```

## Memory Estimation

```mermaid
graph TD
    A[Config] --> B[count_parameters]
    B --> C[num_params]
    C --> D{Training?}
    D -->|Yes| E[Weights + Gradients + Optimizer + Activations]
    D -->|No| F[Weights Only]
    E --> G[Total GB]
    F --> G
    G --> H{Hardware Guidance}
    H -->|<=200M| I[CPU / 8GB GPU]
    H -->|<=1B| J[16GB GPU]
    H -->|<=3B| K[24GB GPU]
    H -->|<=8B| L[2x A100]
    H -->|>8B| M[Multi-GPU Cluster]
```
