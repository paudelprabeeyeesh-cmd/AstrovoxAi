#!/usr/bin/env python3
"""
Astrovox CLI - Command-line interface for Astrovox AI
"""
import argparse
import json
import sys
import os
from typing import Optional, List
from urllib.request import Request, urlopen
from urllib.error import HTTPError

API_BASE = os.environ.get('ASTROVOX_API_URL', 'https://api.astrovox.ai/v1')

def api_request(method: str, path: str, data: Optional[dict] = None, token: Optional[str] = None) -> dict:
    url = f"{API_BASE}{path}"
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"Error {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)

def cmd_send(args: argparse.Namespace) -> int:
    token = os.environ.get('ASTROVOX_API_KEY')
    if not token:
        print("Error: ASTROVOX_API_KEY environment variable not set", file=sys.stderr)
        return 1
    result = api_request('POST', '/chat/message', {
        'conversation_id': args.conversation,
        'message': args.message,
        'model': args.model
    }, token)
    print(result.get('ai_message', {}).get('content', ''))
    return 0

def cmd_conversations(args: argparse.Namespace) -> int:
    token = os.environ.get('ASTROVOX_API_KEY')
    if not token:
        print("Error: ASTROVOX_API_KEY environment variable not set", file=sys.stderr)
        return 1
    result = api_request('GET', '/conversations', token=token)
    for conv in result:
        print(f"{conv['id']}: {conv['title']}")
    return 0

def cmd_create(args: argparse.Namespace) -> int:
    token = os.environ.get('ASTROVOX_API_KEY')
    if not token:
        print("Error: ASTROVOX_API_KEY environment variable not set", file=sys.stderr)
        return 1
    result = api_request('POST', '/conversations', {
        'title': args.title or 'New Conversation',
        'model': args.model or 'gpt-4'
    }, token)
    print(f"Created conversation: {result['id']}")
    return 0

def cmd_stream(args: argparse.Namespace) -> int:
    token = os.environ.get('ASTROVOX_API_KEY')
    if not token:
        print("Error: ASTROVOX_API_KEY environment variable not set", file=sys.stderr)
        return 1
    print("Streaming not implemented in CLI. Use the SDK for streaming.", file=sys.stderr)
    return 1

def cmd_health(args: argparse.Namespace) -> int:
    result = api_request('GET', '/health')
    print(json.dumps(result, indent=2))
    return 0

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Astrovox AI CLI')
    subparsers = parser.add_subparsers(dest='command')

    send_parser = subparsers.add_parser('send', help='Send a message')
    send_parser.add_argument('conversation', help='Conversation ID')
    send_parser.add_argument('message', help='Message to send')
    send_parser.add_argument('--model', default='gpt-4', help='Model to use')

    conv_parser = subparsers.add_parser('conversations', help='List conversations')
    create_parser = subparsers.add_parser('create', help='Create conversation')
    create_parser.add_argument('--title', help='Conversation title')
    create_parser.add_argument('--model', default='gpt-4', help='Model to use')

    stream_parser = subparsers.add_parser('stream', help='Stream a message')
    stream_parser.add_argument('conversation', help='Conversation ID')
    stream_parser.add_argument('message', help='Message to send')

    subparsers.add_parser('health', help='Check API health')

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    commands = {
        'send': cmd_send,
        'conversations': cmd_conversations,
        'create': cmd_create,
        'stream': cmd_stream,
        'health': cmd_health
    }
    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
