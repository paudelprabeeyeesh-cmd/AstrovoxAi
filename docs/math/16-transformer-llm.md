# Section 16 — Transformer and LLM Mathematics

**Level 4 · Central to a language-model assistant** | Topics 635–710  
**Used in AstraVox:** the mathematical core of GPT-like models, fine-tuning, efficient inference, and language-model evaluation.

635. Tokenization and discrete token spaces  
636. Token IDs and vocabulary representations  
637. Token embeddings  
638. Learned positional embeddings  
639. Sinusoidal positional encoding  
640. Rotary positional embeddings (RoPE)  
641. Relative position representations  
642. Query, key, and value projections  
643. Scaled dot-product attention  
644. Attention masking  
645. Causal attention  
646. Multi-head and grouped-query attention  
647. Multi-query attention  
648. Multi-head latent attention  
649. Softmax temperature  
650. Next-token probability distributions  
651. Autoregressive factorization  
652. Teacher forcing  
653. Negative log-likelihood  
654. Cross-entropy training loss  
655. Label smoothing  
656. Logits and log probabilities  
657. Sampling from categorical distributions  
658. Greedy decoding  
659. Top-k sampling  
660. Top-p (nucleus) sampling  
661. Repetition penalties and their mathematical effects  
662. Beam search  
663. Length normalization  
664. Perplexity evaluation  
665. Context-window constraints  
666. Key-value (KV) caching  
667. Attention complexity  
668. Memory and compute complexity  
669. FlashAttention principles  
670. Sparse attention  
671. Linear attention  
672. Sliding-window attention  
673. Long-context scaling  
674. Feed-forward network blocks  
675. Gated MLPs and SwiGLU  
676. RMSNorm and LayerNorm  
677. Residual-stream computation  
678. Pre-normalization versus post-normalization  
679. Transformer parameter counting  
680. Compute and memory estimation  
681. Neural scaling laws  
682. Chinchilla-style compute-optimal training  
683. Data-mixture weighting  
684. Curriculum learning  
685. Supervised fine-tuning objectives  
686. Instruction-tuning objectives  
687. Preference modeling  
688. Reward modeling  
689. Reinforcement learning from human feedback (RLHF)  
690. Proximal policy optimization (PPO)  
691. Direct preference optimization (DPO)  
692. Contrastive preference objectives  
693. Quantization-aware training  
694. Low-rank adaptation (LoRA)  
695. Quantized LoRA (QLoRA)  
696. Weight-only quantization  
697. Activation quantization  
698. Speculative decoding  
699. Mixture-of-experts compute allocation  
700. Retrieval-augmented generation scoring  
701. Embedding similarity and cosine distance  
702. Vector search and approximate nearest neighbors  
703. Reranking objectives  
704. Mathematical evaluation of hallucination rates  
705. Calibration and uncertainty in generated answers  
706. Language-model evaluation statistics  
707. Distributed training and gradient synchronization  
708. Pipeline and tensor parallelism mathematics  
709. Training stability and loss scaling  
710. Inference throughput and latency models  

## AI applications

The mathematical core of GPT-like models, fine-tuning, efficient inference, and language-model evaluation.

## Mapping to code

- `internal/inference/` — attention, KV caching, FlashAttention, decoding, sampling, speculative decoding, throughput/latency (topics 643–648, 666–672, 669, 698, 710; `flash_attention.go`).
- `internal/tokenizer/` — tokenization, token IDs, embeddings, positional encodings (topics 635–641).
- `internal/lora/` and `training/` — LoRA/QLoRA, QAT, fine-tuning, RLHF/DPO, distributed training (topics 685–709).
- `internal/rag/` — RAG scoring, embedding similarity, vector search, reranking (topics 700–703).
- `evals/` — perplexity, hallucination evaluation, calibration, LM evaluation statistics (topics 664, 704–706).
