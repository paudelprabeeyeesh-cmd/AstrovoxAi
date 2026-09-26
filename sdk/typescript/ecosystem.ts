export class EcosystemClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }
  listPlugins(capability) {
    return fetch(`https://api.astrovox.ai/ecosystem/plugins?capability=${capability}`, {
      headers: { Authorization: `Bearer ${this.apiKey}` },
    });
  }
}
