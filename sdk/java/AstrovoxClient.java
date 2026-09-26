import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;

public class AstrovoxClient {
    private final String baseUrl;
    private final String apiKey;
    private final HttpClient client;

    public AstrovoxClient(String apiKey) {
        this(apiKey, "https://api.astrovox.ai/v1");
    }

    public AstrovoxClient(String apiKey, String baseUrl) {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl.replaceAll("/$", "");
        this.client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(30))
                .build();
    }

    private HttpRequest.Builder requestBuilder(String method, String path) {
        return HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .header("Authorization", "Bearer " + apiKey)
                .header("Content-Type", "application/json")
                .method(method, HttpRequest.BodyPublishers.noBody());
    }

    public String sendMessage(String conversationId, String message, String model) throws Exception {
        String body = "{\"conversation_id\":\"" + conversationId + "\",\"message\":\"" + message + "\",\"model\":\"" + model + "\"}";
        HttpRequest request = requestBuilder("POST", "/chat/message")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    public String createConversation(String title, String model) throws Exception {
        String body = "{\"title\":\"" + title + "\",\"model\":\"" + model + "\"}";
        HttpRequest request = requestBuilder("POST", "/conversations")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    public String listConversations() throws Exception {
        HttpRequest request = requestBuilder("GET", "/conversations").build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    public String createWebhook(String url, java.util.List<String> events) throws Exception {
        String body = "{\"url\":\"" + url + "\",\"events\":" + events.toString() + "}";
        HttpRequest request = requestBuilder("POST", "/webhooks")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    public String healthCheck() throws Exception {
        HttpRequest request = requestBuilder("GET", "/health").build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }
}
