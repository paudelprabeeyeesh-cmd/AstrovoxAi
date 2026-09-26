export class CertificationClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }
  verifyModel(modelId) {
    return fetch(`https://api.astrovox.ai/certification/models/${modelId}`, {
      headers: { Authorization: `Bearer ${this.apiKey}` },
    });
  }
}
