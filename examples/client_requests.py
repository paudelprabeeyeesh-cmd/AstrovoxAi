#!/usr/bin/env python3
"""
Raw HTTP client for AstrovoxAI inference server using requests.

Usage:
    python examples/client_requests.py --prompt "Hello, world!"
    python examples/client_requests.py --chat "Tell me a story"
"""

import os
import sys
import json
import argparse
from typing import Optional, List, Dict, Any

try:
    import requests
except ImportError:
    print("Error: requests package not installed. Run: pip install requests")
    sys.exit(1)


class AstrovoxClient:
    """Raw HTTP client for AstrovoxAI inference server."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make an HTTP request."""
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                timeout=kwargs.pop("timeout", 60),
                **kwargs,
            )
            response.raise_for_status()
            if response.content:
                return response.json()
            return {}
        except requests.exceptions.HTTPError as e:
            error_detail = {}
            try:
                error_detail = response.json()
            except Exception:
                error_detail = {"detail": response.text}
            raise RuntimeError(
                f"HTTP {response.status_code}: {error_detail.get('detail', str(e))}"
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(f"Connection error: {e}") from e
        except requests.exceptions.Timeout as e:
            raise RuntimeError(f"Request timeout: {e}") from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Request error: {e}") from e

    def health(self) -> Dict[str, Any]:
        """Check server health."""
        return self._request("GET", "/health")

    def health_ready(self) -> Dict[str, Any]:
        """Check readiness with detailed health status."""
        return self._request("GET", "/health/ready")

    def health_model(self) -> Dict[str, Any]:
        """Check model status."""
        return self._request("GET", "/health/model")

    def completion(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 1.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """Text completion."""
        data = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        return self._request("POST", "/v1/completions", data=data)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 100,
        temperature: float = 1.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """Chat completion."""
        data = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        return self._request("POST", "/v1/chat/completions", data=data)

    def batch(
        self,
        prompts: List[str],
        max_tokens: int = 100,
        temperature: float = 1.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """Batch completion."""
        data = {
            "prompts": prompts,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        return self._request("POST", "/v1/batch", data=data)


def main():
    parser = argparse.ArgumentParser(
        description="Raw HTTP client for AstrovoxAI inference"
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("ASTROVOX_BASE_URL", "http://localhost:8001"),
        help="Base URL for the inference server",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("ASTROVOX_API_KEY", ""),
        help="API key for authentication",
    )
    parser.add_argument(
        "--prompt", help="Text prompt for completion"
    )
    parser.add_argument(
        "--chat", help="Chat prompt (will be sent as user message)"
    )
    parser.add_argument(
        "--messages",
        nargs="+",
        help="Chat messages in format 'role:content'",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=100,
        help="Maximum tokens to generate",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="Sampling temperature",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream the response (not supported in raw client)",
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="Batch prompts",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Check server health",
    )
    parser.add_argument(
        "--health-ready",
        action="store_true",
        help="Check readiness with detailed status",
    )

    args = parser.parse_args()

    client = AstrovoxClient(args.base_url, args.api_key)

    try:
        if args.health:
            result = client.health()
            print(json.dumps(result, indent=2))

        elif args.health_ready:
            result = client.health_ready()
            print(json.dumps(result, indent=2))

        elif args.prompt:
            result = client.completion(
                args.prompt,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            print(result["text"])
            print(f"Tokens: {result.get('total_tokens', 'N/A')}")

        elif args.chat:
            messages = [{"role": "user", "content": args.chat}]
            result = client.chat_completion(
                messages,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            choice = result["choices"][0]
            print(f"{choice['message']['role']}: {choice['message']['content']}")
            print(f"Tokens: {result['usage']['total_tokens']}")

        elif args.messages:
            messages = []
            for msg in args.messages:
                role, content = msg.split(":", 1)
                messages.append({"role": role.strip(), "content": content.strip()})
            result = client.chat_completion(
                messages,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            choice = result["choices"][0]
            print(f"{choice['message']['role']}: {choice['message']['content']}")

        elif args.batch:
            result = client.batch(
                args.batch,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            for i, res in enumerate(result.get("results", [])):
                print(f"[{i}] {res['text']}")

        else:
            parser.print_help()
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
