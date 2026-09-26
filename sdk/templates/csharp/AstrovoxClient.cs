"""C# SDK client template."""
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace AstrovoxSDK;

public class Client
{
    public string ApiKey { get; }
    public string BaseUrl { get; }
    private readonly HttpClient _http;

    public Client(string apiKey, string baseUrl = "https://api.astrovox.ai/v1")
    {
        ApiKey = apiKey;
        BaseUrl = baseUrl;
        _http = new HttpClient();
        _http.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiKey}");
        _http.DefaultRequestHeaders.Add("Accept", "application/json");
    }

    private async Task<HttpResponseMessage> SendAsync(HttpMethod method, string path, object? body = null)
    {
        var request = new HttpRequestMessage(method, BaseUrl + path);
        if (body != null)
        {
            request.Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");
        }
        return await _http.SendAsync(request);
    }

    public async Task<string> SendMessageAsync(string conversationId, string message, string model = "gpt-4")
    {
        var resp = await SendAsync(HttpMethod.Post, "/chat/message", new { conversation_id = conversationId, message, model });
        return await resp.Content.ReadAsStringAsync();
    }

    public async Task<string> CreateConversationAsync(string title, string model = "gpt-4")
    {
        var resp = await SendAsync(HttpMethod.Post, "/conversations", new { title, model });
        return await resp.Content.ReadAsStringAsync();
    }

    public async Task<string> ListConversationsAsync()
    {
        var resp = await SendAsync(HttpMethod.Get, "/conversations");
        return await resp.Content.ReadAsStringAsync();
    }

    public async Task<string> HealthCheckAsync()
    {
        var resp = await SendAsync(HttpMethod.Get, "/health");
        return await resp.Content.ReadAsStringAsync();
    }
}
