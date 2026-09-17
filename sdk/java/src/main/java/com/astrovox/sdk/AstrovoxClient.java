package com.astrovox.sdk;

public class AstrovoxClient {
    private String apiKey;
    private String baseUrl;

    public AstrovoxClient(String apiKey, String baseUrl) {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
    }

    public String getApiKey() {
        return apiKey;
    }
}

