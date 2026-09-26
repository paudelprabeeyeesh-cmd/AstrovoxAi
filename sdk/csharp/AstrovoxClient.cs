using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public class AstrovoxClient
{
    private readonly string _baseUrl;
    private readonly string _apiKey;
    private readonly HttpClient _client;

    public AstrovoxClient(string apiKey, string baseUrl = "https://api.astrovox.ai/v1")
    {
        _apiKey = apiKey;
        _baseUrl = baseUrl.TrimEnd('/');
        _client = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
    }

    private HttpRequestMessage CreateRequest(string method, string path)
    {
        var request = new HttpRequestMessage(new HttpMethod(method), $"{_baseUrl}{path}");
        request.Headers.Add("Authorization", $"Bearer {_apiKey}");
        request.Headers.Add("Content-Type", "application/json");
        return request;
    }

    private async Task<JsonElement> SendAsync(HttpRequestMessage request)
    {
        var response = await _client.SendAsync(request);
        response.EnsureSuccessStatusCode();
        var stream = await response.Content.ReadAsStreamAsync();
        return await JsonSerializer.DeserializeAsync<JsonElement>(stream);
    }

    public async Task<JsonElement> SendMessageAsync(string conversationId, string message, string model = "gpt-4")
    {
        var body = new
        {
            conversation_id = conversationId,
            message = message,
            model = model
        };
        var request = CreateRequest("POST", "/chat/message");
        request.Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");
        return await SendAsync(request);
    }

    public async Task<JsonElement> CreateConversationAsync(string title = "New Conversation", string model = "gpt-4")
    {
        var body = new { title = title, model = model };
        var request = CreateRequest("POST", "/conversations");
        request.Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");
        return await SendAsync(request);
    }

    public async Task<JsonElement> ListConversationsAsync()
    {
        var request = CreateRequest("GET", "/conversations");
        return await SendAsync(request);
    }

    public async Task<JsonElement> CreateWebhookAsync(string url, List<string> events)
    {
        var body = new { url = url, events = events };
        var request = CreateRequest("POST", "/webhooks");
        request.Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");
        return await SendAsync(request);
    }

    public async Task<JsonElement> HealthCheckAsync()
    {
        var request = CreateRequest("GET", "/health");
        return await SendAsync(request);
    }
}
