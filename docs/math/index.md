# AstraVox Mathematics Curriculum

Complete math roadmap organized by **level (0–5)** and **section (1–19)** covering all 851 topics. AstraVox teaches and uses these topics progressively: a beginner never sees a Level 4 equation without Level 0–2 explanation first.

## Levels

| Level | Name | Covers |
|-------|------|--------|
| 0 | Mathematical foundations | Arithmetic, fractions, ratios, units, number systems |
| 1 | Algebra and functions | Equations, inequalities, polynomials, logarithms, functions |
| 2 | Core university mathematics | Calculus, linear algebra, probability, statistics, discrete mathematics |
| 3 | Machine learning mathematics | Gradients, loss functions, optimization, Bayesian inference, information theory |
| 4 | Deep learning and LLMs | Tensors, backpropagation, attention, embeddings, numerical optimization |
| 5 | Advanced and research mathematics | Measure theory, advanced optimization, geometry, causal inference, control theory |

## Sections

| # | Section | Topics | Level | Used in AstraVox |
|---|---------|--------|-------|------------------|
| 1 | Foundations: arithmetic and number systems | 1–30 | 0 | `tensor/math`, data preprocessing |
| 2 | Algebra: from elementary to advanced | 31–68 | 1 | symbolic math, equation solving |
| 3 | Functions, graphs, and mathematical modeling | 69–96 | 1 | activation functions, regression |
| 4 | Geometry and trigonometry | 97–126 | 0–5 | computer vision, 3D graphics, robotics |
| 5 | Linear algebra | 127–175 | 2 | `tensor/math`, embeddings, attention |
| 6 | Calculus: how quantities change | 176–215 | 2–3 | `autograd`, backprop, gradient descent |
| 7 | Optimization mathematics | 216–257 | 3–4 | training, hyperparameter tuning |
| 8 | Probability theory | 258–313 | 2–3 | uncertainty, sampling, generative AI |
| 9 | Statistics and data analysis | 314–375 | 2 | A/B testing, confidence, forecasting |
| 10 | Information theory | 376–405 | 3 | next-token prediction, perplexity, compression |
| 11 | Discrete mathematics and CS mathematics | 406–455 | 2 | search, planning, symbolic reasoning |
| 12 | Numerical analysis and scientific computing | 457–491 | 4–5 | `tensor/math`, GPU, low-precision inference |
| 13 | Differential equations and dynamical systems | 492–518 | 5 | scientific ML, continuous-depth networks |
| 14 | Mathematical foundations of machine learning | 519–573 | 3 | conventional ML models, evaluation |
| 15 | Deep learning mathematics | 574–634 | 4 | neural networks, pruning, distillation |
| 16 | Transformer and LLM mathematics | 635–710 | 4 | GPT core, fine-tuning, inference, eval |
| 17 | Search, recommendation, and knowledge systems | 711–736 | 4 | document search, memory retrieval, KG |
| 18 | Reinforcement learning and decision mathematics | 737–775 | 3–4 | agents, planning, sequential decisions |
| 19 | Advanced mathematics for AI research | 776–851 | 5 | research, formal verification, DP, federated |

## How to use this curriculum

- **Beginners**: work sections 1–3 (Level 0–1) before touching ML.
- **Deep learning / LLM work**: sections 5, 6, 7, 10, 14, 15, 16 (Level 2–4).
- **Research**: sections 12, 13, 18, 19 (Level 4–5).
- Each section file lists every topic in order with its AI applications. Code pointers show where AstraVox implements the corresponding math.
