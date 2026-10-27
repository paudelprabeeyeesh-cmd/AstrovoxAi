# Section 14 — Mathematical Foundations of Machine Learning

**Level 3** | Topics 519–573  
**Used in AstraVox:** practically every conventional machine-learning model, reliable evaluation, and selecting the right approach for a particular task.

519. Supervised learning objectives  
520. Unsupervised learning objectives  
521. Semi-supervised learning  
522. Self-supervised learning  
523. Loss-function design  
524. Empirical risk minimization  
525. Expected risk minimization  
526. Training, validation, and test distributions  
527. Generalization error  
528. Overfitting and underfitting  
529. Bias–variance trade-off  
530. Regularization  
531. L1 and L2 penalties  
532. Weight decay  
533. Early stopping  
534. Cross-validation  
535. Feature scaling and normalization  
536. Feature selection  
537. Feature engineering mathematics  
538. Linear and polynomial regression  
539. Logistic regression  
540. Naive Bayes  
541. k-nearest neighbors  
542. Decision trees  
543. Random forests  
544. Gradient-boosted trees  
545. Support vector machines  
546. Kernel methods  
547. Gaussian processes  
548. Clustering objectives  
549. k-means optimization  
550. Density-based clustering  
551. Mixture models  
552. Expectation–maximization  
553. Dimensionality reduction  
554. PCA and kernel PCA  
555. Manifold learning  
556. Spectral clustering  
557. Metric learning  
558. Ranking and learning-to-rank  
559. Calibration of predictions  
560. Distribution shift  
561. Domain adaptation  
562. Transfer learning  
563. Few-shot learning  
564. Active learning  
565. Semi-parametric learning  
566. Online learning  
567. Continual learning  
568. Concept drift  
569. Ensemble methods  
570. Interpretability and feature attribution  
571. Conformal prediction  
572. Robustness and adversarial examples  
573. Fairness metrics and their mathematical trade-offs  

## AI applications

Practically every conventional machine-learning model, reliable evaluation, and selecting the right approach for a particular task.

## Mapping to code

- `training/` (`pretrain.py`, `finetune.py`, `metrics.py`, `checkpoint.py`) — loss design, ERM, regularization, cross-validation, early stopping, calibration (topics 523–534, 559).
- `internal/ml/` and conventional models — regression, Naive Bayes, k-NN, trees, SVMs, kernel methods, GPs, clustering, EM (topics 538–552).
- `internal/grounding/` — distribution shift, domain adaptation, transfer learning, concept drift, fairness (topics 560–563, 568, 573).
