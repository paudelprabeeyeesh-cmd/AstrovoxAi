"""API Platform — REST, GraphQL, gRPC, API versioning, SDK generation."""

import json
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class APIEndpoint:
    """API endpoint definition."""
    path: str
    method: str
    description: str
    parameters: list = None
    response_schema: dict = None
    auth_required: bool = True

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []


class OpenAPIGenerator:
    """Generate OpenAPI specification."""

    def __init__(self, title: str, version: str, description: str = ""):
        self._title = title
        self._version = version
        self._description = description
        self._endpoints: list[APIEndpoint] = []

    def add_endpoint(self, endpoint: APIEndpoint):
        """Add an endpoint."""
        self._endpoints.append(endpoint)

    def generate(self) -> dict:
        """Generate OpenAPI spec."""
        paths = {}
        for ep in self._endpoints:
            if ep.path not in paths:
                paths[ep.path] = {}
            paths[ep.path][ep.method.lower()] = {
                "description": ep.description,
                "parameters": ep.parameters,
                "responses": {
                    "200": {"description": "Success"},
                    "401": {"description": "Unauthorized"},
                    "404": {"description": "Not Found"},
                },
            }

        return {
            "openapi": "3.0.0",
            "info": {
                "title": self._title,
                "version": self._version,
                "description": self._description,
            },
            "paths": paths,
        }


class SDKGenerator:
    """Generate SDK code for different languages."""

    @staticmethod
    def generate_python_sdk(endpoints: list[APIEndpoint]) -> str:
        """Generate Python SDK code."""
        code = """\"\"\"AstrovoxAI Python SDK\"\"\"
import httpx

class AstrovoxClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.client = httpx.Client(headers={"Authorization": f"Bearer {api_key}"})

"""
        for ep in endpoints:
            method_name = ep.path.replace("/", "_").strip("_")
            code += f"""
    def {method_name}(self, **kwargs):
        \"\"\"{ep.description}\"\"\"
        return self.client.{ep.method.lower()}("{ep.path}", json=kwargs).json()

"""
        return code

    @staticmethod
    def generate_javascript_sdk(endpoints: list[APIEndpoint]) -> str:
        """Generate JavaScript SDK code."""
        code = """// AstrovoxAI JavaScript SDK
class AstrovoxClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.headers = { Authorization: `Bearer ${apiKey}` };
    }

"""
        for ep in endpoints:
            method_name = ep.path.replace("/", "_").strip("_")
            code += f"""
    async {methodName}(params = {{}}) {{
        // {ep.description}
        const response = await fetch(`${{this.baseUrl}}{ep.path}`, {{
            method: '{ep.method}',
            headers: this.headers,
            body: JSON.stringify(params),
        }});
        return response.json();
    }}

"""
        return code


openapi_generator = OpenAPIGenerator("AstrovoxAI API", "2.0.0")
sdk_generator = SDKGenerator()
