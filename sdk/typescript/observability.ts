export class ObservabilityClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }
  recordTrace(trace) {
    return fetch("https://api.astrovox.ai/observability/traces", {
      method: "POST",
      headers: { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify(trace),
    });
  }
}
