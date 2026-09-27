#!/usr/bin/env python3
"""
OpenAI-compatible client for AstrovoxAI inference server.

Usage:
    python examples/client_openai.py --prompt "Hello, world!"
    python examples/client_openai.py --chat "Tell me a story"
"""

import os
import sys
import argparse
from typing import Optional, List, Dict, Any

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)


def create_client(base_url: str, api_key: str) -> OpenAI:
    """Create an OpenAI client configured for AstrovoxAI."""
    return OpenAI(
        base_url=base_url,
        api_key=api_key or "sk-placeholder",
    )


def completion_example(client: OpenAI, prompt: str, **kwargs) -> Dict[str, Any]:
    """Text completion example."""
    response = client.completions.create(
        model="astrovox",
        prompt=prompt,
        max_tokens=kwargs.get("max_tokens", 100),
        temperature=kwargs.get("temperature", 1.0),
        top_p=kwargs.get("top_p", None),
        stop=kwargs.get("stop", None),
    )
    return response.model_dump()


def chat_completion_example(
    client: OpenAI, messages: List[Dict[str, str]], **kwargs
) -> Dict[str, Any]:
    """Chat completion example."""
    response = client.chat.completions.create(
        model="astrovox-chat",
        messages=messages,
        max_tokens=kwargs.get("max_tokens", 100),
        temperature=kwargs.get("temperature", 1.0),
        top_p=kwargs.get("top_p", None),
        stop=kwargs.get("stop", None),
        stream=kwargs.get("stream", False),
    )
    if kwargs.get("stream", False):
        print("Streaming response:")
        for chunk in response:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print()
        return {"streamed": True}
    return response.model_dump()


def batch_completion_example(
    client: OpenAI, prompts: List[str], **kwargs
) -> Dict[str, Any]:
    """Batch completion example."""
    response = client.post(
        "/v1/batch",
        json={
            "prompts": prompts,
            "max_tokens": kwargs.get("max_tokens", 100),
            "temperature": kwargs.get("temperature", 1.0),
        },
    )
    return response.json()


def main():
    parser = argparse.ArgumentParser(
        description="OpenAI-compatible client for AstrovoxAI inference"
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("ASTROVOX_BASE_URL", "http://localhost:8001/v1"),
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
        help="Stream the response",
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="Batch prompts",
    )

    args = parser.parse_args()

    client = create_client(args.base_url, args.api_key)

    try:
        if args.prompt:
            result = completion_example(
                client, args.prompt,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            print(result["choices"][0]["text"])

        elif args.chat:
            messages = [{"role": "user", "content": args.chat}]
            result = chat_completion_example(
                client, messages,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                stream=args.stream,
            )
            if not args.stream:
                choice = result["choices"][0]
                print(f"{choice['message']['role']}: {choice['message']['content']}")
                print(f"Tokens: {result['usage']['total_tokens']}")

        elif args.messages:
            messages = []
            for msg in args.messages:
                role, content = msg.split(":", 1)
                messages.append({"role": role.strip(), "content": content.strip()})
            result = chat_completion_example(
                client, messages,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                stream=args.stream,
            )
            if not args.stream:
                choice = result["choices"][0]
                print(f"{choice['message']['role']}: {choice['message']['content']}")

        elif args.batch:
            result = batch_completion_example(
                client, args.batch,
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
