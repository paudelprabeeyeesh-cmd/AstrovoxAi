# Section 5 — Linear Algebra

**Level 2 · Essential for deep learning and LLMs** | Topics 127–175  
**Used in AstraVox:** `tensor/math`, embeddings, neural network layers, attention, dimensionality reduction, recommendation systems, model compression, efficient GPU computation.

127. Scalars, vectors, matrices, tensors  
128. Vector addition and scalar multiplication  
129. Dot products and vector norms  
130. Vector angles and orthogonality  
131. Matrix addition and multiplication  
132. Transpose and identity matrices  
133. Matrix inverse  
134. Determinants  
135. Rank and null space  
136. Systems of linear equations  
137. Gaussian elimination  
138. Row-reduced echelon form  
139. Column space and row space  
140. Linear independence and dependence  
141. Basis and dimension  
142. Vector spaces and subspaces  
143. Linear transformations  
144. Change of basis  
145. Eigenvalues and eigenvectors  
146. Characteristic polynomials  
147. Diagonalization  
148. Symmetric and orthogonal matrices  
149. Positive-definite matrices  
150. Singular value decomposition (SVD)  
151. QR decomposition  
152. LU decomposition  
153. Cholesky decomposition  
154. Matrix norms and condition numbers  
155. Least-squares problems  
156. Projection matrices  
157. Gram–Schmidt orthogonalization  
158. Principal component analysis (PCA)  
159. Low-rank approximation  
160. Sparse matrices  
161. Block matrices  
162. Kronecker products  
163. Tensor products  
164. Tensor contractions  
165. Matrix calculus  
166. Vector-Jacobian products  
167. Jacobian and Hessian matrices  
168. Spectral theory  
169. Numerical linear algebra  
170. Random matrices  
171. Matrix factorization  
172. Latent-factor models  
173. Multilinear algebra  
174. Tensor decompositions  
175. Operator theory  

## AI applications

Embeddings, neural network layers, attention, dimensionality reduction, recommendation systems, model compression, and efficient GPU computation.

## Mapping to code

- `tensor/math/` — GEMM (`gemm.go`), norms (`norm.go`), FFT (`fft.go`), quantization (`quant.go`), fused activations (`fused_act.go`), BLAS, SIMD kernels (topics 127–175).
- `internal/rag/` and `internal/vectordb/` — SVD, low-rank approximation, vector similarity, latent-factor models.
