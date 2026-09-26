"""OpenAPI specification generator."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json


@dataclass
class SchemaProperty:
    name: str
    type: str
    required: bool = False
    description: str = ""
    example: Any = None


@dataclass
class EndpointSpec:
    path: str
    method: str
    summary: str
    description: str = ""
    parameters: List[SchemaProperty] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[int, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    auth_required: bool = False


class OpenAPISpecGenerator:
    _endpoints: List[EndpointSpec] = []

    @classmethod
    def add_endpoint(cls, endpoint: EndpointSpec) -> None:
        cls._endpoints.append(endpoint)

    @classmethod
    def generate(cls, title: str = "AstrovoxAi API", version: str = "2.0.0") -> Dict[str, Any]:
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": title,
                "version": version,
                "description": "AstrovoxAi Backend API Specification",
            },
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    },
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                    },
                },
            },
        }

        for endpoint in cls._endpoints:
            path_item = spec["paths"].setdefault(endpoint.path, {})
            operation = {
                "summary": endpoint.summary,
                "description": endpoint.description,
                "responses": {
                    str(code): {"description": desc} for code, desc in endpoint.responses.items()
                },
                "tags": endpoint.tags,
            }
            if endpoint.auth_required:
                operation["security"] = [{"BearerAuth": []}]
            if endpoint.request_body:
                operation["requestBody"] = endpoint.request_body
            path_item[endpoint.method.lower()] = operation

        return spec

    @classmethod
    def to_json(cls, **kwargs) -> str:
        return json.dumps(cls.generate(**kwargs), indent=2)

    @classmethod
    def to_yaml(cls, **kwargs) -> str:
        import yaml
        return yaml.dump(cls.generate(**kwargs), default_flow_style=False)
