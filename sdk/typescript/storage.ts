export class StorageClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }
  saveCheckpoint(checkpoint) {
    return fetch("https://api.astrovox.ai/storage/checkpoints", {
      method: "POST",
      headers: { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify(checkpoint),
    });
  }
}
