# Section 15 — Deep Learning Mathematics

**Level 4** | Topics 574–634  
**Used in AstraVox:** designing, training, compressing, and debugging neural networks.

574. Artificial neuron equations  
575. Weighted sums and biases  
576. Activation functions  
577. Sigmoid and tanh  
578. ReLU and Leaky ReLU  
579. GELU and SiLU  
580. Softmax  
581. Feed-forward neural networks  
582. Computational graphs  
583. Forward propagation  
584. Loss gradients  
585. Backpropagation  
586. Chain-rule differentiation through networks  
587. Vanishing gradients  
588. Exploding gradients  
589. Weight initialization  
590. Xavier and He initialization  
591. Batch normalization  
592. Layer normalization  
593. RMS normalization  
594. Residual connections  
595. Dropout  
596. Weight tying  
597. Embedding layers  
598. Convolution operations  
599. Convolutional neural networks  
600. Pooling operations  
601. Recurrent neural networks  
602. Long short-term memory (LSTM)  
603. Gated recurrent units (GRU)  
604. Attention mechanisms  
605. Self-attention  
606. Multi-head attention  
607. Positional encodings  
608. Residual stream analysis  
609. Gradient checkpointing mathematics  
610. Truncated backpropagation through time  
611. Neural-network regularization  
612. Loss landscapes  
613. Neural tangent kernels  
614. Double descent  
615. Scaling laws  
616. Neural-network pruning  
617. Knowledge distillation  
618. Low-rank adaptation mathematics  
619. Quantization mathematics  
620. Neural architecture search  
621. Equivariant neural networks  
622. Geometric deep learning  
623. Graph neural networks  
624. Generative adversarial networks  
625. Variational autoencoders  
626. Diffusion models  
627. Score matching  
628. Energy-based models  
629. Normalizing flows  
630. Contrastive learning  
631. Representation learning  
632. Self-distillation  
633. Sparse neural networks  
634. Mixture-of-experts routing mathematics  

## AI applications

Designing, training, compressing, and debugging neural networks.

## Mapping to code

- `tensor/math/` — fused activations (sigmoid, tanh, ReLU, GELU, softmax), layer norm, RMS norm, residual, flash attention (topics 576–580, 591–593, 607; `fused_act.go`, `norm.go`, `flash_attention.go`).
- `internal/model/` — feed-forward, RNN, LSTM, GRU, attention, GNN, VAE, diffusion, GAN, MoE (topics 581–606, 623–634).
- `internal/lora/` and quantization — LoRA, quantization math, pruning, distillation (topics 616–619, 633–634).
