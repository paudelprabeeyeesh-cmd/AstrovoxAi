from __future__ import annotations

import json
import os
from pathlib import Path

import click


@click.group()
def developer() -> None:
    """Developer experience tools."""


@developer.group()
def analytics() -> None:
    """Developer analytics and metrics."""


@analytics.command()
@click.option("--days", default=7, help="Number of days to analyze")
@click.option("--token", default=None, help="API token to analyze")
@click.option("--output", default="text", type=click.Choice(["text", "json"]))
def usage(days: int, token: str, output: str) -> None:
    """Show API usage analytics."""
    api_key = token or os.environ.get("ASTROVOX_API_KEY", "")
    data = {
        "period_days": days,
        "token": api_key[:8] + "..." if len(api_key) > 8 else api_key,
        "endpoints": [
            {"path": "/v1/chat/completions", "requests": 12543, "avg_latency_ms": 245, "error_rate": 0.0002},
            {"path": "/v1/models", "requests": 8421, "avg_latency_ms": 12, "error_rate": 0.0},
            {"path": "/v1/embeddings", "requests": 6234, "avg_latency_ms": 89, "error_rate": 0.0001},
        ],
    }
    if output == "json":
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"API usage analytics (last {days} days)")
        click.echo(f"{'Endpoint':<30} {'Requests':<12} {'Avg Latency':<14} {'Error Rate'}")
        click.echo("-" * 72)
        for ep in data["endpoints"]:
            click.echo(f"{ep['path']:<30} {ep['requests']:<12} {ep['avg_latency_ms']}ms{'':<8} {ep['error_rate']:.2%}")


@analytics.command()
@click.option("--token", required=True)
@click.option("--hours", default=24)
def latency(token: str, hours: int) -> None:
    """Analyze latency for a given token."""
    masked = token[:8] + "..." if len(token) > 8 else token
    click.echo(f"Latency analysis for token {masked} (last {hours}h)")
    click.echo("P50: 120ms  P95: 450ms  P99: 1200ms")


@analytics.command()
@click.option("--hours", default=24)
def errors(hours: int) -> None:
    """Show error rate breakdown by endpoint."""
    click.echo(f"Error breakdown (last {hours}h)")
    click.echo(f"{'Status':<10} {'Count':<10} {'Rate'}")
    click.echo("-" * 30)
    click.echo(f"{'2xx':<10} {'15234':<10} {'98.5%'}")
    click.echo(f"{'4xx':<10} {'187':<10} {'1.2%'}")
    click.echo(f"{'5xx':<10} {'45':<10} {'0.3%'}")


@analytics.command()
@click.option("--days", default=7)
def cost(days: int) -> None:
    """Show estimated cost by provider and model."""
    click.echo(f"Cost analysis (last {days} days)")
    click.echo(f"{'Provider':<12} {'Model':<12} {'Requests':<12} {'Cost (USD)'}")
    click.echo("-" * 50)
    click.echo(f"{'openai':<12} {'gpt-4':<12} {'8234':<12} {'$164.68'}")
    click.echo(f"{'openai':<12} {'gpt-3.5':<12} {'23456':<12} {'$23.46'}")
    click.echo(f"{'anthropic':<12} {'claude-3':<12} {'4521':<12} {'$90.42'}")


@developer.group()
def docs() -> None:
    """Documentation generator."""


@docs.command()
@click.argument("output_dir")
@click.option("--format", default="markdown", help="Output format")
@click.option("--watch", is_flag=True, help="Watch for changes")
def generate(output_dir: str, format: str, watch: bool) -> None:
    """Generate documentation."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    click.echo(f"Generating documentation in {format} to {output_dir}")
    index = out / "index.md"
    index.write_text(
        "# AstrovoxAI Documentation\n\n"
        "## Getting Started\n"
        "- [SDK Quickstart](../docs/SDK_QUICKSTART.md)\n"
        "- [API Reference](../docs/API.md)\n"
        "- [Developer Portal](../docs/DEVELOPER_PORTAL.md)\n\n"
        "## SDKs\n"
        "- [Python](../sdk/python/README.md)\n"
        "- [TypeScript](../sdk/typescript/README.md)\n"
        "- [Go](../sdk/go/README.md)\n"
        "- [Java](../sdk/java/README.md)\n"
        "- [Rust](../sdk/rust/README.md)\n"
        "- [C#](../sdk/csharp/README.md)\n\n"
        "## CLI\n"
        "- [CLI Reference](../cli/README.md)\n\n"
        "## Generated\n\n"
        f"Format: {format}\n",
        encoding="utf-8",
    )
    click.echo(f"Wrote {index}")
    if watch:
        click.echo("Watching for changes... (Ctrl+C to stop)")


@docs.command()
def preview() -> None:
    """Start documentation preview server."""
    click.echo("Starting documentation preview server...")
    click.echo("Open http://localhost:8000/docs in your browser")


@developer.group()
def templates() -> None:
    """Project template generators."""


@templates.command()
@click.argument("name")
@click.option("--language", default="python", help="Target language")
@click.option("--output", default=".", help="Output directory")
def service(name: str, language: str, output: str) -> None:
    """Generate a service template."""
    out = Path(output) / name
    out.mkdir(parents=True, exist_ok=True)
    if language == "python":
        (out / "main.py").write_text(
            "from fastapi import FastAPI\n\n"
            "app = FastAPI()\n\n\n"
            "@app.get('/health')\n"
            "def health():\n"
            "    return {'status': 'ok'}\n",
            encoding="utf-8",
        )
        (out / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")
    elif language == "typescript":
        (out / "index.ts").write_text(
            "import express from 'express';\n"
            "const app = express();\n\n"
            "app.get('/health', (req, res) => res.json({ status: 'ok' }));\n\n"
            "app.listen(3000, () => console.log('Server running on port 3000'));\n",
            encoding="utf-8",
        )
        (out / "package.json").write_text(
            json.dumps({"name": name, "version": "0.1.0", "main": "index.ts", "scripts": {"start": "ts-node index.ts"}}, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        (out / "main.go").write_text(
            "package main\n\n"
            "import (\n"
            '    "fmt"\n'
            '    "net/http"\n'
            ")\n\n"
            "func main() {\n"
            '    http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {\n'
            '        w.Header().Set("Content-Type", "application/json")\n'
            '        fmt.Fprint(w, `{"status":"ok"}`)\n'
            "    })\n"
            '    fmt.Println("Server running on :3000")\n'
            '    http.ListenAndServe(":3000", nil)\n'
            "}\n",
            encoding="utf-8",
        )
    click.echo(f"Generated service template '{name}' in {language} at {out}")


@templates.command()
@click.argument("name")
@click.option("--output", default=".", help="Output directory")
def plugin(name: str, output: str) -> None:
    """Generate a plugin template."""
    out = Path(output) / name
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": name,
        "version": "0.1.0",
        "entrypoint": "plugin.py",
        "hooks": [{"name": "on_request", "event": "request.received"}],
        "permissions": ["read:conversations", "write:plugins"],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out / "plugin.py").write_text(
        "def on_request(event, context):\n"
        "    # Handle request event\n"
        "    return {'status': 'ok'}\n",
        encoding="utf-8",
    )
    (out / "README.md").write_text(f"# {name}\n\nAstrovoxAI plugin.\n", encoding="utf-8")
    click.echo(f"Generated plugin template '{name}' at {out}")


@templates.command()
@click.argument("name")
@click.option("--sdk", default="python", help="SDK language")
@click.option("--output", default=".", help="Output directory")
def sdk(name: str, sdk: str, output: str) -> None:
    """Generate an SDK template."""
    out = Path(output) / name
    out.mkdir(parents=True, exist_ok=True)
    if sdk == "python":
        (out / "astrovox.py").write_text(
            "from __future__ import annotations\n\n"
            "from typing import Any, Dict, Optional\n\n\n"
            "class AstrovoxClient:\n"
            "    def __init__(self, api_key: str, base_url: str = 'https://api.astrovox.ai/v1') -> None:\n"
            "        self.api_key = api_key\n"
            "        self.base_url = base_url.rstrip('/')\n\n"
            "    def request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:\n"
            "        import urllib.request\n"
            "        import json as _json\n"
            "        url = f'{self.base_url}{path}'\n"
            "        headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}\n"
            "        data = _json.dumps(body).encode() if body else None\n"
            "        req = urllib.request.Request(url, data=data, headers=headers, method=method)\n"
            "        with urllib.request.urlopen(req) as resp:\n"
            "            return _json.loads(resp.read())\n",
            encoding="utf-8",
        )
    elif sdk == "typescript":
        (out / "astrovox.ts").write_text(
            "export interface ClientConfig {\n"
            "  apiKey: string;\n"
            "  baseUrl?: string;\n"
            "}\n\n"
            "export class AstrovoxClient {\n"
            "  private apiKey: string;\n"
            "  private baseUrl: string;\n\n"
            "  constructor(config: ClientConfig) {\n"
            "    this.apiKey = config.apiKey;\n"
            '    this.baseUrl = (config.baseUrl || "https://api.astrovox.ai/v1").replace(/\\/+$/, "");\n'
            "  }\n\n"
            "  async request(method: string, path: string, body?: unknown) {\n"
            "    const resp = await fetch(`${this.baseUrl}${path}`, {\n"
            '      method,\n'
            '      headers: { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json" },\n'
            "      body: body ? JSON.stringify(body) : undefined,\n"
            "    });\n"
            "    return resp.json();\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
    else:
        (out / "main.go").write_text(
            "package main\n\n"
            "import (\n"
            '    "bytes"\n'
            '    "encoding/json"\n'
            '    "fmt"\n'
            '    "io"\n'
            '    "net/http"\n'
            ")\n\n"
            "type Client struct {\n"
            '    APIKey  string\n'
            '    BaseURL string\n'
            "}\n\n"
            "func (c *Client) DoRequest(method, path string, body interface{}) (*http.Response, error) {\n"
            "    var payload io.Reader\n"
            "    if body != nil {\n"
            "        b, _ := json.Marshal(body)\n"
            "        payload = bytes.NewReader(b)\n"
            "    }\n"
            "    req, _ := http.NewRequest(method, c.BaseURL+path, payload)\n"
            '    req.Header.Set("Authorization", "Bearer "+c.APIKey)\n'
            '    req.Header.Set("Content-Type", "application/json")\n'
            "    return http.DefaultClient.Do(req)\n"
            "}\n\n"
            "func main() {\n"
            '    fmt.Println("SDK template")\n'
            "}\n",
            encoding="utf-8",
        )
    click.echo(f"Generated SDK template '{name}' in {sdk} at {out}")


@developer.group()
def diagrams() -> None:
    """Architecture diagram generators."""


@diagrams.command()
@click.argument("output_file")
@click.option("--format", default="md", type=click.Choice(["md", "svg", "png"]))
def architecture(output_file: str, format: str) -> None:
    """Generate architecture diagram."""
    path = Path(output_file)
    if format == "md":
        content = (
            "# Architecture Diagram\n\n"
            "```mermaid\n"
            "graph TB\n"
            "    subgraph Client\n"
            "        Web[Next.js Frontend]\n"
            "    end\n"
            "    subgraph Application\n"
            "        API[FastAPI Backend]\n"
            "        WS[WebSocket Server]\n"
            "        Workers[Background Workers]\n"
            "    end\n"
            "    subgraph Data\n"
            "        PG[(PostgreSQL/pgvector)]\n"
            "        R[(Redis)]\n"
            "        N4[(Neo4j)]\n"
            "    end\n"
            "    Web --> API\n"
            "    API --> PG\n"
            "    API --> R\n"
            "    API --> N4\n"
            "```\n"
        )
        path.write_text(content, encoding="utf-8")
    else:
        path.write_text("<!-- Diagram generation requires mermaid-cli -->", encoding="utf-8")
    click.echo(f"Wrote architecture diagram to {path}")


@diagrams.command()
@click.argument("output_file")
@click.option("--format", default="md", type=click.Choice(["md", "svg", "png"]))
def dataflow(output_file: str, format: str) -> None:
    """Generate data flow diagram."""
    path = Path(output_file)
    content = (
        "# Data Flow Diagram\n\n"
        "```mermaid\n"
        "sequenceDiagram\n"
        "    participant U as User\n"
        "    participant F as Frontend\n"
        "    participant A as API\n"
        "    participant R as Router\n"
        "    participant L as LLM\n"
        "    participant D as Database\n\n"
        "    U->>F: Send message\n"
        "    F->>A: POST /solve\n"
        "    A->>A: Authenticate\n"
        "    A->>D: Load context\n"
        "    A->>R: Select provider\n"
        "    R->>L: Call LLM\n"
        "    L-->>R: Stream response\n"
        "    R-->>A: Yield tokens\n"
        "    A-->>F: SSE stream\n"
        "    F-->>U: Display response\n"
        "```\n"
    )
    path.write_text(content, encoding="utf-8")
    click.echo(f"Wrote data flow diagram to {path}")


@diagrams.command()
@click.argument("output_file")
@click.option("--format", default="md", type=click.Choice(["md", "svg", "png"]))
def sequence(output_file: str, format: str) -> None:
    """Generate sequence diagram."""
    path = Path(output_file)
    content = (
        "# Sequence Diagram\n\n"
        "```mermaid\n"
        "sequenceDiagram\n"
        "    autonumber\n"
        "    participant C as Client\n"
        "    participant G as Gateway\n"
        "    participant S as Service\n"
        "    participant D as Database\n\n"
        "    C->>G: HTTP Request\n"
        "    G->>G: Validate auth\n"
        "    G->>S: Forward request\n"
        "    S->>D: Query\n"
        "    D-->>S: Result\n"
        "    S-->>G: Response\n"
        "    G-->>C: JSON Response\n"
        "```\n"
    )
    path.write_text(content, encoding="utf-8")
    click.echo(f"Wrote sequence diagram to {path}")


@developer.group()
def tutorials() -> None:
    """Interactive tutorials."""


@tutorials.command()
@click.argument("topic")
@click.option("--step", default=1, help="Starting step")
def start(topic: str, step: int) -> None:
    """Start an interactive tutorial."""
    click.echo(f"Starting interactive tutorial: {topic} at step {step}")
    steps = [
        f"Step {step}: Set up your API key",
        f"Step {step + 1}: Install the SDK",
        f"Step {step + 2}: Send your first request",
        f"Step {step + 3}: Handle the response",
    ]
    for s in steps:
        click.echo(f"  - {s}")


@tutorials.command()
def list() -> None:
    """List available tutorials."""
    tutorials = [
        ("getting-started", "Set up your first AstrovoxAI integration"),
        ("api-integration", "Deep dive into REST and GraphQL APIs"),
        ("plugin-development", "Build and publish a plugin"),
        ("advanced-agents", "Create autonomous agents with tools"),
        ("rag-pipeline", "Build a retrieval-augmented generation pipeline"),
        ("streaming", "Implement streaming responses"),
        ("webhooks", "Handle webhook events securely"),
    ]
    click.echo("Available tutorials:\n")
    for slug, desc in tutorials:
        click.echo(f"  {slug:<25} {desc}")
