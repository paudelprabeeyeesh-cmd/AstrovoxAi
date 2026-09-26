"""SDK documentation generator."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional


class SDKDocsGenerator:
    def __init__(self, sdk_root: Path, output_dir: Path) -> None:
        self.sdk_root = sdk_root
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, languages: Optional[List[str]] = None) -> Dict[str, Path]:
        languages = languages or ["python", "typescript", "go", "java", "rust", "csharp"]
        generated: Dict[str, Path] = {}
        for lang in languages:
            lang_dir = self.sdk_root / lang
            if not lang_dir.exists():
                continue
            readme = self._render_readme(lang)
            out = self.output_dir / lang / "README.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(readme, encoding="utf-8")
            generated[lang] = out
        index = self._render_index(languages)
        index_out = self.output_dir / "README.md"
        index_out.write_text(index, encoding="utf-8")
        generated["index"] = index_out
        return generated

    def _render_readme(self, language: str) -> str:
        examples = {
            "python": (
                "import astrovox\n\n"
                "client = astrovox.AstrovoxClient(api_key='your-key')\n"
                "conversation = client.create_conversation(title='My Chat')\n"
                "response = client.send_message(conversation.id, 'Hello!')\n"
                "print(response['ai_message']['content'])\n"
            ),
            "typescript": (
                "import { AstrovoxClient } from '@astrovox/sdk'\n\n"
                "const client = new AstrovoxClient({ apiKey: 'your-key' })\n"
                "const conversation = await client.createConversation({ title: 'My Chat' })\n"
                "const response = await client.sendMessage({ conversationId: conversation.id, message: 'Hello!' })\n"
                "console.log(response.ai_message.content)\n"
            ),
            "go": (
                'package main\n\nimport "github.com/astrovox/sdk/go"\n\n'
                "client := astrovox.NewClient('your-key')\n"
                "conversation, _ := client.CreateConversation('My Chat', 'gpt-4')\n"
                "response, _ := client.SendMessage(conversation.ID, 'Hello!')\n"
                "fmt.Println(response.AIMessage.Content)\n"
            ),
            "java": (
                "AstrovoxClient client = new AstrovoxClient('your-key');\n"
                "String response = client.sendMessage(conversationId, 'Hello!', 'gpt-4');\n"
                "System.out.println(response);\n"
            ),
            "rust": (
                "use astrovox_sdk::AstrovoxClient;\n\n"
                "let client = AstrovoxClient::new('your-key', None);\n"
                "let conversation = client.create_conversation('My Chat', 'gpt-4').await?;\n"
                "let response = client.send_message(&conversation.id, 'Hello!').await?;\n"
                "println!('{}', response.ai_message.content);\n"
            ),
            "csharp": (
                'var client = new Client("your-key");\n'
                "var resp = await client.SendMessageAsync(conversationId, 'Hello!');\n"
                "Console.WriteLine(resp);\n"
            ),
        }
        return (
            f"# Astrovox SDK - {language.title()}\n\n"
            "## Installation\n\n"
            f"See [{language}/README.md](./{language}/README.md) for installation instructions.\n\n"
            "## Quick Start\n\n"
            "```{}\n".format(language)
            + examples.get(language, "# Example code")
            + "\n```\n\n"
            "## Features\n\n"
            "- Conversation management\n"
            "- Message sending and streaming\n"
            "- Multi-provider AI support\n"
            "- Agent creation and management\n"
            "- Tool/plugin integration\n"
            "- File uploads and RAG\n"
            "- Webhook signature verification\n"
            "- Typed error handling\n"
            "- Retry logic with exponential backoff\n"
        )

    def _render_index(self, languages: List[str]) -> str:
        lines = ["# Astrovox SDKs\n\n", "Official SDKs for multiple languages.\n\n"]
        for lang in languages:
            lines.append(f"- [{lang.title()}](./{lang}/README.md)\n")
        lines.append("\n## Features\n\n")
        lines.append("- Conversation management\n")
        lines.append("- Message sending and streaming\n")
        lines.append("- Multi-provider AI support\n")
        lines.append("- Agent creation and management\n")
        lines.append("- Tool/plugin integration\n")
        lines.append("- File uploads and RAG\n")
        return "".join(lines)
