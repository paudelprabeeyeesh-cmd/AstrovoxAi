# Section 10 — Information Theory

**Level 3 · Critical for language models** | Topics 376–405  
**Used in AstraVox:** next-token prediction, language-model evaluation, token distributions, compression, knowledge representation, comparing probability distributions.

376. Information and uncertainty  
377. Self-information  
378. Entropy  
379. Joint entropy  
380. Conditional entropy  
381. Mutual information  
382. Conditional mutual information  
383. Cross-entropy  
384. Kullback–Leibler (KL) divergence  
385. Jensen–Shannon divergence  
386. Differential entropy  
387. Relative entropy  
388. Information gain  
389. Perplexity  
390. Maximum entropy principle  
391. Data-processing inequality  
392. Source coding  
393. Shannon's source coding theorem  
394. Huffman coding  
395. Arithmetic coding  
396. Channel capacity  
397. Noisy-channel models  
398. Rate-distortion theory  
399. Minimum description length  
400. Information bottleneck  
401. Algorithmic information theory  
402. Kolmogorov complexity  
403. Coding theory  
404. Error-correcting codes  
405. Entropy regularization  

## AI applications

Next-token prediction, language-model evaluation, token distributions, compression, knowledge representation, and comparing probability distributions.

## Mapping to code

- `internal/inference/` and decoding — cross-entropy, KL divergence, perplexity, entropy regularization (topics 383–384, 389, 405).
- `internal/tokenizer/` — source coding, Huffman/arithmetic coding, token distributions (topics 392–395).
- `internal/knowledge/` — information bottleneck, mutual information for knowledge representation (topics 381, 400).
