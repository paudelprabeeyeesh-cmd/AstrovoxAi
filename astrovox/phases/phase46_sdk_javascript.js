"""Official JavaScript/TypeScript SDK for Astrovox API."""

// Official Astrovox JavaScript SDK

class AstrovoxSDK {
    constructor(config) {
        this.apiKey = config?.apiKey || "";
        this.baseUrl = config?.baseURL || "https://api.astrovox.ai/v1";
        this.timeout = config?.timeout || 30000;
    }

    _request(method, path, data) {
        return fetch(this.baseUrl + path, {
            method,
            headers: {
                "Authorization": `Bearer ${this.apiKey}`,
                "Content-Type": "application/json"
            },
            body: data ? JSON.stringify(data) : null
        }).then(r => r.json());
    }

    async chat(messages, model = "astrovox") {
        return this._request("POST", "/chat", { messages, model });
    }

    async embed(text, model = "astrovox-embed") {
        const r = await this._request("POST", "/embeddings", { input: text, model });
        return r.embedding || [];
    }

    async search(query, options = {}) {
        return this._request("GET", "/search", { q: query, ...options });
    }

    async transcribe(audio, language = "en") {
        const blob = new Blob([audio]);
        const fd = new FormData();
        fd.append("audio", blob);
        return fetch(this.baseUrl + "/transcribe", {
            method: "POST",
            headers: { "Authorization": `Bearer ${this.apiKey}` },
            body: fd
        }).then(r => r.text());
    }

    async versions() {
        return this._request("GET", "/models");
    }

    async health() {
        return this._request("GET", "/health");
    }
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = { AstrovoxSDK };
}
