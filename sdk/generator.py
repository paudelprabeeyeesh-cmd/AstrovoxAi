from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sdk.openapi.spec import OpenAPISpec


@dataclass
class ClientConfig:
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3


class SDKGenerator:
    def __init__(self, spec: OpenAPISpec, output_dir: Path) -> None:
        self.spec = spec
        self.output_dir = output_dir

    def generate(self) -> Dict[str, Path]:
        generated: Dict[str, Path] = {}
        python_dir = self.output_dir / "python"
        python_dir.mkdir(parents=True, exist_ok=True)
        ts_dir = self.output_dir / "typescript"
        ts_dir.mkdir(parents=True, exist_ok=True)
        go_dir = self.output_dir / "go"
        go_dir.mkdir(parents=True, exist_ok=True)
        java_dir = self.output_dir / "java"
        java_dir.mkdir(parents=True, exist_ok=True)
        rust_dir = self.output_dir / "rust"
        rust_dir.mkdir(parents=True, exist_ok=True)
        csharp_dir = self.output_dir / "csharp"
        csharp_dir.mkdir(parents=True, exist_ok=True)

        generated["python"] = self._write_python(python_dir)
        generated["typescript"] = self._write_typescript(ts_dir)
        generated["go"] = self._write_go(go_dir)
        generated["java"] = self._write_java(java_dir)
        generated["rust"] = self._write_rust(rust_dir)
        generated["csharp"] = self._write_csharp(csharp_dir)
        return generated

    def _write_python(self, target: Path) -> Path:
        main = target / "astrovox.py"
        content = self._render_python_client()
        main.write_text(content, encoding="utf-8")
        init = target / "__init__.py"
        init.write_text("from .astrovox import AstrovoxClient\n", encoding="utf-8")
        return main

    def _render_python_client(self) -> str:
        return (
            "from __future__ import annotations\n\n"
            "import asyncio\n"
            "import inspect\n"
            "from typing import Any, Dict, List, Optional\n\n"
            "import httpx\n\n\n"
            "class AstrovoxError(Exception):\n"
            "    def __init__(self, message: str, status: Optional[int] = None) -> None:\n"
            "        super().__init__(message)\n"
            "        self.status = status\n\n\n"
            "class AstrovoxClient:\n"
            "    def __init__(self, config: ClientConfig) -> None:\n"
            "        self.base_url = config.base_url.rstrip(\"/\")\n"
            "        self.api_key = config.api_key\n"
            "        self.timeout = config.timeout\n"
            "        self.max_retries = config.max_retries\n\n"
            "    def _headers(self) -> Dict[str, str]:\n"
            "        headers: Dict[str, str] = {\"Accept\": \"application/json\"}\n"
            "        if self.api_key:\n"
            '            headers["Authorization"] = f"Bearer {self.api_key}"\n'
            "        return headers\n\n"
            "    async def request(\n"
            "        self, method: str, path: str, body: Optional[Dict[str, Any]] = None\n"
            "    ) -> Any:\n"
            "        url = f\"{self.base_url}{path}\"\n"
            "        async with httpx.AsyncClient(timeout=self.timeout) as client:\n"
            "            response = await client.request(\n"
            "                method=method, url=url, json=body, headers=self._headers()\n"
            "            )\n"
            "        if response.status_code >= 400:\n"
            "            raise AstrovoxError(response.text, status=response.status_code)\n"
            "        if response.status_code == 204:\n"
            "            return None\n"
            "        return response.json()\n\n"
        )

    def _write_typescript(self, target: Path) -> Path:
        main = target / "astrovox.ts"
        content = self._render_typescript_client()
        main.write_text(content, encoding="utf-8")
        pkg = target / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "name": "@astrovox/sdk",
                    "version": "0.1.0",
                    "main": "astrovox.js",
                    "types": "astrovox.d.ts",
                    "scripts": {"build": "tsc"},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return main

    def _render_typescript_client(self) -> str:
        return (
            "export interface ClientConfig {\n"
            "  baseUrl: string;\n"
            "  apiKey?: string;\n"
            "  timeout?: number;\n"
            "}\n\n"
            "export class AstrovoxError extends Error {\n"
            "  status?: number;\n"
            "  constructor(message: string, status?: number) {\n"
            "    super(message);\n"
            "    this.status = status;\n"
            "  }\n"
            "}\n\n"
            "export class AstrovoxClient {\n"
            "  private baseUrl: string;\n"
            "  private apiKey?: string;\n"
            "  private timeout: number;\n\n"
            "  constructor(config: ClientConfig) {\n"
            "    this.baseUrl = config.baseUrl.replace(/\\/+$/, \"\");\n"
            "    this.apiKey = config.apiKey;\n"
            "    this.timeout = config.timeout ?? 30000;\n"
            "  }\n\n"
            "  private headers(): Record<string, string> {\n"
            '    const headers: Record<string, string> = { Accept: \"application/json\" };\n'
            "    if (this.apiKey) headers[\"Authorization\"] = `Bearer ${this.apiKey}`;\n"
            "    return headers;\n"
            "  }\n\n"
            "  async request(method: string, path: string, body?: unknown): Promise<unknown> {\n"
            "    const response = await fetch(`${this.baseUrl}${path}`, {\n"
            "      method,\n"
            "      headers: this.headers(),\n"
            "      body: body ? JSON.stringify(body) : undefined,\n"
            "    });\n"
            "    if (!response.ok) {\n"
            "      const text = await response.text();\n"
            "      throw new AstrovoxError(text, response.status);\n"
            "    }\n"
            "    if (response.status === 204) return null;\n"
            "    return response.json();\n"
            "  }\n"
            "}\n"
        )

    def _write_go(self, target: Path) -> Path:
        main = target / "astrovox.go"
        content = self._render_go_client()
        main.write_text(content, encoding="utf-8")
        mod = target / "go.mod"
        mod.write_text(
            "module github.com/astrovox/sdk/go\n\ngo 1.21\n\nrequire github.com/astrovox/sdk v0.1.0\n",
            encoding="utf-8",
        )
        return main

    def _render_go_client(self) -> str:
        return (
            "package sdk\n\n"
            "import (\n"
            '\t"bytes"\n'
            '\t"encoding/json"\n'
            '\t"fmt"\n'
            '\t"io"\n'
            '\t"net/http"\n'
            '\t"time"\n'
            ")\n\n"
            "type RetryPolicy struct {\n"
            "\tMaxRetries      int\n"
            "\tBackoffFactor   float64\n"
            "\tRetryableStatus []int\n"
            "}\n\n"
            "type Client struct {\n"
            "\tAPIKey       string\n"
            "\tBaseURL      string\n"
            "\tHTTP         *http.Client\n"
            "\tRetryPolicy  RetryPolicy\n"
            "}\n\n"
            "type Message struct {\n"
            '\tRole      string `json:"role"`\n'
            '\tContent   string `json:"content"`\n'
            '\tTimestamp string `json:"timestamp,omitempty"`\n'
            "}\n\n"
            "type Conversation struct {\n"
            '\tID        string    `json:"id"`\n'
            '\tTitle     string    `json:"title"`\n'
            '\tMessages  []Message `json:"messages,omitempty"`\n'
            '\tModel     string    `json:"model"`\n'
            '\tCreatedAt string    `json:"created_at,omitempty"`\n'
            "}\n\n"
            "func NewClient(apiKey, baseURL string) *Client {\n"
            "\treturn &Client{\n"
            "\t\tAPIKey: apiKey,\n"
            "\t\tBaseURL: baseURL,\n"
            "\t\tHTTP: &http.Client{Timeout: 30 * time.Second},\n"
            "\t\tRetryPolicy: RetryPolicy{\n"
            "\t\t\tMaxRetries:    3,\n"
            "\t\t\tBackoffFactor: 1.0,\n"
            "\t\t\tRetryableStatus: []int{429, 500, 502, 503, 504},\n"
            "\t\t},\n"
            "\t}\n"
            "}\n\n"
            "func (c *Client) DoRequest(method, path string, body interface{}) (*http.Response, error) {\n"
            "\tvar payload io.Reader\n"
            "\tif body != nil {\n"
            "\t\tb, err := json.Marshal(body)\n"
            "\t\tif err != nil {\n"
            "\t\t\treturn nil, err\n"
            "\t\t}\n"
            "\t\tpayload = bytes.NewReader(b)\n"
            "\t}\n"
            "\treq, err := http.NewRequest(method, c.BaseURL+path, payload)\n"
            "\tif err != nil {\n"
            "\t\treturn nil, err\n"
            "\t}\n"
            '\treq.Header.Set("Authorization", "Bearer "+c.APIKey)\n'
            '\treq.Header.Set("Content-Type", "application/json")\n'
            "\tresp, err := c.HTTP.Do(req)\n"
            "\tif err != nil {\n"
            "\t\treturn nil, err\n"
            "\t}\n"
            "\treturn resp, nil\n"
            "}\n\n"
            "func (c *Client) SendMessage(conversationID, message, model string) (map[string]interface{}, error) {\n"
            "\tresp, err := c.DoRequest(\"POST\", \"/chat/message\", map[string]interface{}{\n"
            "\t\t\"conversation_id\": conversationID,\n"
            "\t\t\"message\":         message,\n"
            "\t\t\"model\":           model,\n"
            "\t})\n"
            "\tif err != nil {\n"
            "\t\treturn nil, err\n"
            "\t}\n"
            "\tdefer resp.Body.Close()\n"
            "\tvar result map[string]interface{}\n"
            "\tif err := json.NewDecoder(resp.Body).Decode(&result); err != nil {\n"
            "\t\treturn nil, err\n"
            "\t}\n"
            "\treturn result, nil\n"
            "}\n\n"
            "func (c *Client) CreateConversation(title, model string) (*Conversation, error) {\n"
            "\tresp, err := c.DoRequest(\"POST\", \"/conversations\", map[string]interface{}{\n"
            "\t\t\"title\": title,\n"
            "\t\t\"model\": model,\n"
            "\t})\n"
            "\tif err != nil {\n"
            "\t\treturn nil, err\n"
            "\t}\n"
            "\tdefer resp.Body.Close()\n"
            "\tvar conv Conversation\n"
            "\tif err := json.NewDecoder(resp.Body).Decode(&conv); err != nil {\n"
            "\t\treturn nil, err\n"
            "\t}\n"
            "\treturn &conv, nil\n"
            "}\n\n"
            "func (c *Client) HealthCheck() (map[string]interface{}, error) {\n"
            "\tresp, err := c.DoRequest(\"GET\", \"/health\", nil)\n"
            "\tif err != nil {\n"
            "\t\treturn nil, err\n"
            "\t}\n"
            "\tdefer resp.Body.Close()\n"
            "\tvar result map[string]interface{}\n"
            "\tif err := json.NewDecoder(resp.Body).Decode(&result); err != nil {\n"
            "\t\treturn nil, err\n"
            "\t}\n"
            "\treturn result, nil\n"
            "}\n\n"
            "func (c *Client) String() string {\n"
            "\treturn fmt.Sprintf(\"AstrovoxClient(base_url=%s)\", c.BaseURL)\n"
            "}\n"
        )

    def _write_java(self, target: Path) -> Path:
        main = target / "AstrovoxClient.java"
        content = self._render_java_client()
        main.write_text(content, encoding="utf-8")
        pom = target / "pom.xml"
        pom.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<project xmlns="http://maven.apache.org/POM/4.0.0"\n'
            '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
            '         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">\n'
            '    <modelVersion>4.0.0</modelVersion>\n'
            '    <groupId>com.astrovox</groupId>\n'
            '    <artifactId>astrovox-sdk</artifactId>\n'
            '    <version>0.1.0</version>\n'
            "</project>\n",
            encoding="utf-8",
        )
        return main

    def _render_java_client(self) -> str:
        return (
            "import java.net.URI;\n"
            "import java.net.http.HttpClient;\n"
            "import java.net.http.HttpRequest;\n"
            "import java.net.http.HttpResponse;\n"
            "import java.time.Duration;\n\n"
            "public class AstrovoxClient {\n"
            "    private final String baseUrl;\n"
            "    private final String apiKey;\n"
            "    private final HttpClient client;\n\n"
            "    public AstrovoxClient(String apiKey) {\n"
            "        this(apiKey, \"https://api.astrovox.ai/v1\");\n"
            "    }\n\n"
            "    public AstrovoxClient(String apiKey, String baseUrl) {\n"
            "        this.apiKey = apiKey;\n"
            "        this.baseUrl = baseUrl.replaceAll(\"/$\", \"\");\n"
            "        this.client = HttpClient.newBuilder()\n"
            "                .connectTimeout(Duration.ofSeconds(30))\n"
            "                .build();\n"
            "    }\n\n"
            "    private HttpRequest.Builder requestBuilder(String method, String path) {\n"
            "        return HttpRequest.newBuilder()\n"
            "                .uri(URI.create(baseUrl + path))\n"
            "                .header(\"Authorization\", \"Bearer \" + apiKey)\n"
            "                .header(\"Content-Type\", \"application/json\")\n"
            "                .method(method, HttpRequest.BodyPublishers.noBody());\n"
            "    }\n\n"
            "    public String sendMessage(String conversationId, String message, String model) throws Exception {\n"
            "        String body = String.format(\"{\\\"conversation_id\\\":\\\"%s\\\",\\\"message\\\":\\\"%s\\\",\\\"model\\\":\\\"%s\\\"}\",\n"
            "                conversationId, message, model);\n"
            "        HttpRequest request = requestBuilder(\"POST\", \"/chat/message\")\n"
            "                .POST(HttpRequest.BodyPublishers.ofString(body))\n"
            "                .build();\n"
            "        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());\n"
            "        return response.body();\n"
            "    }\n\n"
            "    public String createConversation(String title, String model) throws Exception {\n"
            "        String body = String.format(\"{\\\"title\\\":\\\"%s\\\",\\\"model\\\":\\\"%s\\\"}\", title, model);\n"
            "        HttpRequest request = requestBuilder(\"POST\", \"/conversations\")\n"
            "                .POST(HttpRequest.BodyPublishers.ofString(body))\n"
            "                .build();\n"
            "        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());\n"
            "        return response.body();\n"
            "    }\n\n"
            "    public String listConversations() throws Exception {\n"
            "        HttpRequest request = requestBuilder(\"GET\", \"/conversations\").build();\n"
            "        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());\n"
            "        return response.body();\n"
            "    }\n\n"
            "    public String healthCheck() throws Exception {\n"
            "        HttpRequest request = requestBuilder(\"GET\", \"/health\").build();\n"
            "        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());\n"
            "        return response.body();\n"
            "    }\n"
            "}\n"
        )

    def _write_rust(self, target: Path) -> Path:
        main = target / "src" / "lib.rs"
        main.parent.mkdir(parents=True, exist_ok=True)
        content = self._render_rust_client()
        main.write_text(content, encoding="utf-8")
        cargo = target / "Cargo.toml"
        cargo.write_text(
            '[package]\n'
            'name = "astrovox-sdk"\n'
            'version = "0.1.0"\n'
            'edition = "2021"\n\n'
            '[dependencies]\n'
            'reqwest = { version = "0.11", features = ["json"] }\n'
            'serde_json = "1.0"\n'
            'tokio = { version = "1", features = ["full"] }\n',
            encoding="utf-8",
        )
        return main

    def _render_rust_client(self) -> str:
        return (
            "use reqwest::Client;\n"
            "use serde_json::Value;\n\n"
            "pub struct AstrovoxClient {\n"
            "    pub base_url: String,\n"
            "    pub api_key: String,\n"
            "    pub client: Client,\n"
            "}\n\n"
            "impl AstrovoxClient {\n"
            "    pub fn new(api_key: &str, base_url: Option<&str>) -> Self {\n"
            "        let base = base_url.unwrap_or(\"https://api.astrovox.ai/v1\").trim_end_matches('/');\n"
            "        Self {\n"
            "            base_url: base.to_string(),\n"
            "            api_key: api_key.to_string(),\n"
            "            client: Client::builder().timeout(std::time::Duration::from_secs(30)).build().unwrap(),\n"
            "        }\n"
            "    }\n\n"
            "    pub async fn request(&self, method: &str, path: &str, body: Option<Value>) -> Result<Value, reqwest::Error> {\n"
            "        let url = format!(\"{}{}\", self.base_url, path);\n"
            "        let mut req = self.client.request(method.parse().unwrap(), &url)\n"
            "            .header(\"Authorization\", format!(\"Bearer {}\", self.api_key))\n"
            "            .header(\"Content-Type\", \"application/json\");\n"
            "        if let Some(b) = body {\n"
            "            req = req.json(&b);\n"
            "        }\n"
            "        let resp = req.send().await?;\n"
            "        resp.json().await\n"
            "    }\n\n"
            "    pub async fn send_message(&self, conversation_id: &str, message: &str, model: &str) -> Result<Value, reqwest::Error> {\n"
            "        let body = serde_json::json!({\n"
            '            "conversation_id": conversation_id,\n'
            '            "message": message,\n'
            '            "model": model\n'
            "        });\n"
            "        self.request(\"POST\", \"/chat/message\", Some(body)).await\n"
            "    }\n\n"
            "    pub async fn create_conversation(&self, title: &str, model: &str) -> Result<Value, reqwest::Error> {\n"
            "        let body = serde_json::json!({\n"
            '            "title": title,\n'
            '            "model": model\n'
            "        });\n"
            "        self.request(\"POST\", \"/conversations\", Some(body)).await\n"
            "    }\n\n"
            "    pub async fn list_conversations(&self) -> Result<Value, reqwest::Error> {\n"
            "        self.request(\"GET\", \"/conversations\", None).await\n"
            "    }\n\n"
            "    pub async fn health_check(&self) -> Result<Value, reqwest::Error> {\n"
            "        self.request(\"GET\", \"/health\", None).await\n"
            "    }\n"
            "}\n"
        )

    def _write_csharp(self, target: Path) -> Path:
        main = target / "AstrovoxClient.cs"
        content = self._render_csharp_client()
        main.write_text(content, encoding="utf-8")
        proj = target / "AstrovoxSDK.csproj"
        proj.write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n'
            "  <PropertyGroup>\n"
            '    <TargetFramework>net6.0</TargetFramework>\n'
            '    <GeneratePackageOnBuild>true</GeneratePackageOnBuild>\n'
            '    <PackageId>AstrovoxSDK</PackageId>\n'
            '    <Version>0.1.0</Version>\n'
            "  </PropertyGroup>\n"
            "</Project>\n",
            encoding="utf-8",
        )
        return main

    def _render_csharp_client(self) -> str:
        return (
            "using System;\n"
            "using System.Net.Http;\n"
            "using System.Text;\n"
            "using System.Text.Json;\n"
            "using System.Threading.Tasks;\n\n"
            "namespace AstrovoxSDK;\n\n"
            "public class Client\n"
            "{\n"
            '    public string ApiKey { get; }\n'
            '    public string BaseUrl { get; }\n'
            "    private readonly HttpClient _http;\n\n"
            '    public Client(string apiKey, string baseUrl = "https://api.astrovox.ai/v1")\n'
            "    {\n"
            "        ApiKey = apiKey;\n"
            "        BaseUrl = baseUrl;\n"
            "        _http = new HttpClient();\n"
            '        _http.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiKey}");\n'
            '        _http.DefaultRequestHeaders.Add("Accept", "application/json");\n'
            "    }\n\n"
            "    private async Task<HttpResponseMessage> SendAsync(HttpMethod method, string path, object? body = null)\n"
            "    {\n"
            "        var request = new HttpRequestMessage(method, BaseUrl + path);\n"
            "        if (body != null)\n"
            "        {\n"
            '            request.Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");\n'
            "        }\n"
            "        return await _http.SendAsync(request);\n"
            "    }\n\n"
            '    public async Task<string> SendMessageAsync(string conversationId, string message, string model = "gpt-4")\n'
            "    {\n"
            "        var resp = await SendAsync(HttpMethod.Post, \"/chat/message\", new { conversation_id = conversationId, message, model });\n"
            "        return await resp.Content.ReadAsStringAsync();\n"
            "    }\n\n"
            '    public async Task<string> CreateConversationAsync(string title, string model = "gpt-4")\n'
            "    {\n"
            "        var resp = await SendAsync(HttpMethod.Post, \"/conversations\", new { title, model });\n"
            "        return await resp.Content.ReadAsStringAsync();\n"
            "    }\n\n"
            "    public async Task<string> ListConversationsAsync()\n"
            "    {\n"
            "        var resp = await SendAsync(HttpMethod.Get, \"/conversations\");\n"
            "        return await resp.Content.ReadAsStringAsync();\n"
            "    }\n\n"
            "    public async Task<string> HealthCheckAsync()\n"
            "    {\n"
            "        var resp = await SendAsync(HttpMethod.Get, \"/health\");\n"
            "        return await resp.Content.ReadAsStringAsync();\n"
            "    }\n"
            "}\n"
        )
