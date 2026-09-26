package com.astrovox.sdk;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;

public class AstrovoxClient {
    private final String apiKey;
    private final String baseUrl;
    private final HttpClient httpClient;

    public AstrovoxClient(String apiKey, String baseUrl) {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl != null ? baseUrl : "https://api.astrovox.ai/v1";
        this.httpClient = HttpClient.newHttpClient();
    }

    private HttpRequest.Builder requestBuilder(String method, String path) {
        return HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .header("Authorization", "Bearer " + apiKey)
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(30));
    }

    public String sendMessage(String conversationId, String message, String model) throws IOException, InterruptedException {
        String body = String.format("{\"conversation_id\":\"%s\",\"message\":\"%s\",\"model\":\"%s\"}", conversationId, message, model);
        HttpRequest request = requestBuilder("POST", "/chat/message").POST(HttpRequest.BodyPublishers.ofString(body)).build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    public String createConversation(String title, String model) throws IOException, InterruptedException {
        String body = String.format("{\"title\":\"%s\",\"model\":\"%s\"}", title, model);
        HttpRequest request = requestBuilder("POST", "/conversations").POST(HttpRequest.BodyPublishers.ofString(body)).build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    public String listConversations() throws IOException, InterruptedException {
        HttpRequest request = requestBuilder("GET", "/conversations").build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    public String healthCheck() throws IOException, InterruptedException {
        HttpRequest request = requestBuilder("GET", "/health").build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    public String getApiKey() {
        return apiKey;
    }

    public String getBaseUrl() {
        return baseUrl;
    }
}
