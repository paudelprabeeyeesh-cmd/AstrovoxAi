# Section 7 — Optimization Mathematics

**Level 3–4** | Topics 216–257  
**Used in AstraVox:** training neural networks, tuning models, minimizing errors, selecting hyperparameters, resource allocation, improving inference pipelines.

216. Objective and loss functions  
217. Feasible regions and constraints  
218. Local versus global optima  
219. Convex sets  
220. Convex functions  
221. Convex optimization  
222. Gradient descent  
223. Stochastic gradient descent (SGD)  
224. Mini-batch gradient descent  
225. Momentum  
226. Nesterov acceleration  
227. AdaGrad  
228. RMSProp  
229. Adam and AdamW  
230. Learning-rate schedules  
231. Line search  
232. Newton's method  
233. Quasi-Newton methods  
234. BFGS and L-BFGS  
235. Coordinate descent  
236. Proximal gradient methods  
237. Lagrange multipliers  
238. Karush–Kuhn–Tucker (KKT) conditions  
239. Linear programming  
240. Quadratic programming  
241. Integer and mixed-integer optimization  
242. Dynamic programming  
243. Combinatorial optimization  
244. Genetic and evolutionary optimization  
245. Bayesian optimization  
246. Hyperparameter optimization  
247. Multi-objective optimization  
248. Pareto optimality  
249. Robust optimization  
250. Stochastic optimization  
251. Distributed optimization  
252. Convergence analysis  
253. Gradient clipping and conditioning  
254. Trust-region methods  
255. Optimal control  
256. Bilevel optimization  
257. Meta-learning optimization  

## AI applications

Training neural networks, tuning models, minimizing errors, selecting hyperparameters, resource allocation, and improving inference pipelines.

## Mapping to code

- `internal/optimizer/` — SGD, Adam, momentum, learning-rate schedules, gradient clipping (topics 222–230, 253).
- `training/` — hyperparameter optimization, convergence analysis, distributed optimization (topics 246, 251–252).
- `internal/rl/` — optimal control, bilevel, meta-learning (topics 255–257).
