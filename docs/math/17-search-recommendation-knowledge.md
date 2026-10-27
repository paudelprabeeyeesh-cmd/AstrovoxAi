# Section 17 — Search, Recommendation, and Knowledge Systems

**Level 4** | Topics 711–736  
**Used in AstraVox:** document search, memory retrieval, educational-resource search, recommendations, and knowledge graphs.

711. Vector similarity measures  
712. Cosine similarity and distance  
713. Euclidean and Manhattan distances  
714. Mahalanobis distance  
715. Jaccard similarity  
716. Hamming distance  
717. Approximate nearest-neighbor search  
718. Locality-sensitive hashing  
719. Product quantization  
720. Information retrieval scoring  
721. TF-IDF  
722. BM25  
723. Learning-to-rank losses  
724. Collaborative filtering  
725. Matrix-factorization recommenders  
726. Implicit-feedback objectives  
727. Graph embeddings  
728. Knowledge graph embeddings  
729. Link prediction  
730. Graph traversal and search  
731. PageRank and random walks  
732. Bayesian recommendation  
733. Diversity and novelty metrics  
734. Hybrid retrieval scoring  
735. Reciprocal rank fusion  
736. Calibration of retrieval confidence  

## AI applications

AstraVox's document search, memory retrieval, educational-resource search, recommendations, and knowledge graphs.

## Mapping to code

- `internal/rag/` and `internal/retrieval/` — vector similarity, ANN, LSH, product quantization, TF-IDF, BM25, hybrid scoring, RRF (topics 711–719, 720–722, 734–735).
- `internal/vectordb/` — cosine/Euclidean/Mahalanobis/Jaccard/Hamming distances, approximate nearest neighbors (topics 712–717).
- `internal/knowledge/` — graph embeddings, KG embeddings, link prediction, PageRank, graph traversal (topics 727–731).
- Recommendation modules — collaborative filtering, matrix factorization, implicit feedback, Bayesian recommendation (topics 724–726, 732).
