export class MLOpsClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }
  logMetrics(experimentId, metrics) {
    return fetch("https://api.astrovox.ai/mlops/metrics", {
      method: "POST",
      headers: { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ experiment_id: experimentId, metrics }),
    });
  }
}
