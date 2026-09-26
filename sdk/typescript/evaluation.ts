export class EvaluationClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }
  runBenchmark(modelId, benchmarkName) {
    return fetch(`https://api.astrovox.ai/evaluation/benchmarks/${benchmarkName}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model_id: modelId }),
    });
  }
}
