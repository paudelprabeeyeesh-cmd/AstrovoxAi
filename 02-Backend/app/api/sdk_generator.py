"""SDK code generator for multiple languages."""

import logging
from typing import List

from app.api_platform import APIEndpoint

logger = logging.getLogger(__name__)


class SDKGenerator:
    @staticmethod
    def generate_python(endpoints: List[APIEndpoint]) -> str:
        lines = ['"""AstrovoxAI Python SDK."""', "import httpx", "from typing import Optional, Dict, Any", "", "class AstrovoxClient:", '    def __init__(self, api_key: str, base_url: str = "https://api.astrovox.ai/v1"):', '        self.base_url = base_url.rstrip("/")', '        self.client = httpx.Client(headers={"Authorization": f"Bearer {api_key}"}, timeout=30)', ""]
        for ep in endpoints:
            method_name = ep.path.replace("/", "_").strip("_")
            lines.extend([
                f"    def {method_name}(self, **kwargs) -> Dict[str, Any]:",
                f'        """{ep.description}"""',
                f'        return self.client.{ep.method.lower()}("{ep.path}", json=kwargs).json()',
                "",
            ])
        return "\n".join(lines)

    @staticmethod
    def generate_typescript(endpoints: List[APIEndpoint]) -> str:
        lines = ["// AstrovoxAI TypeScript SDK", "export class AstrovoxClient {", "  private apiKey: string;", "  private baseUrl: string;", "", '  constructor(apiKey: string, baseUrl: string = "https://api.astrovox.ai/v1") {', "    this.apiKey = apiKey;", "    this.baseUrl = baseUrl.replace(/\\/$/, '');", "  }", ""]
        for ep in endpoints:
            method_name = ep.path.replace("/", "_").strip("_")
            lines.extend([
                f"  async {method_name}(params: Record<string, any> = {{}}): Promise<any> {{",
                f'    const response = await fetch(`${{this.baseUrl}}{ep.path}`, {{',
                f"      method: '{ep.method}',",
                '      headers: { "Authorization": `Bearer ${{this.apiKey}}`, "Content-Type": "application/json" },',
                "      body: JSON.stringify(params),",
                "    });",
                "    return response.json();",
                "  }",
                "",
            ])
        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def generate_go(endpoints: List[APIEndpoint]) -> str:
        lines = ["package astrovox", "", "type Client struct {", "    BaseURL string", "    APIKey  string", "    Client  *http.Client", "}", ""]
        for ep in endpoints:
            method_name = ep.path.replace("/", "_").strip("_")
            lines.extend([
                f"func (c *Client) {method_name}(params map[string]interface{{}}) (*http.Response, error) {{",
                f'    return c.Client.Do(c.newRequest("{ep.method}", "{ep.path}", params))',
                "}",
                "",
            ])
        return "\n".join(lines)

    @staticmethod
    def generate_java(endpoints: List[APIEndpoint]) -> str:
        lines = ["public class AstrovoxClient {", "    private String baseUrl;", "    private String apiKey;", "    private HttpClient client;", ""]
        for ep in endpoints:
            method_name = ep.path.replace("/", "_").strip("_")
            lines.extend([
                f"    public String {method_name}(Map<String, Object> params) throws Exception {{",
                f'        return this.client.send("{ep.path}", "{ep.method}", params);',
                "    }",
                "",
            ])
        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def generate_rust(endpoints: List[APIEndpoint]) -> str:
        lines = ["use reqwest::Client;", "use serde_json::Value;", "", "pub struct AstrovoxClient {", "    base_url: String,", "    api_key: String,", "    client: Client,", "}", ""]
        for ep in endpoints:
            method_name = ep.path.replace("/", "_").strip("_")
            lines.extend([
                f"impl AstrovoxClient {{",
                f"    pub async fn {method_name}(&self, params: Value) -> Result<Value, reqwest::Error> {{",
                f'        self.client.{ep.method.lower()}("{{}}/{{}}", self.base_url, "{ep.path}")',
                "            .json(&params)",
                "            .send()",
                "            .await?",
                "            .json()",
                "    }",
                "}",
                "",
            ])
        return "\n".join(lines)

    @staticmethod
    def generate_csharp(endpoints: List[APIEndpoint]) -> str:
        lines = ["using System;", "using System.Net.Http;", "using System.Text.Json;", "using System.Threading.Tasks;", "", "public class AstrovoxClient {", "    private readonly HttpClient _client;", "", '    public AstrovoxClient(string apiKey, string baseUrl = "https://api.astrovox.ai/v1") {', "        _client = new HttpClient();", '        _client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiKey}");', "    }", ""]
        for ep in endpoints:
            method_name = ep.path.replace("/", "_").strip("_")
            lines.extend([
                f"    public async Task<JsonElement> {method_name}(Dictionary<string, object> parameters) {{",
                f'        var response = await _client.{ep.method.ToLower()}Async($"{ep.path}", parameters);',
                "        return await response.Content.ReadFromJsonAsync<JsonElement>();",
                "    }",
                "",
            ])
        lines.append("}")
        return "\n".join(lines)


sdk_generator = SDKGenerator()
