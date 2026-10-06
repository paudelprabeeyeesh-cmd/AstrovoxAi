"""Phase 58 - Integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GitHubIntegration:
    repo: str
    token: str = ""
    events: list[str] = field(default_factory=list)


@dataclass
class GitLabIntegration:
    project: str
    token: str = ""
    events: list[str] = field(default_factory=list)


@dataclass
class VSCodeIntegration:
    extension_id: str
    version: str = ""


@dataclass
class DiscordIntegration:
    bot_token: str = ""
    channel_id: str = ""


@dataclass
class SlackIntegration:
    bot_token: str = ""
    channel: str = ""


@dataclass
class NotionIntegration:
    token: str = ""
    database_id: str = ""


class Integrations:
    def __init__(self) -> None:
        self.github: GitHubIntegration | None = None
        self.gitlab: GitLabIntegration | None = None
        self.vscode: VSCodeIntegration | None = None
        self.discord: DiscordIntegration | None = None
        self.slack: SlackIntegration | None = None
        self.notion: NotionIntegration | None = None

    def connect_github(self, integration: GitHubIntegration) -> None:
        self.github = integration

    def connect_gitlab(self, integration: GitLabIntegration) -> None:
        self.gitlab = integration

    def connect_vscode(self, integration: VSCodeIntegration) -> None:
        self.vscode = integration

    def connect_discord(self, integration: DiscordIntegration) -> None:
        self.discord = integration

    def connect_slack(self, integration: SlackIntegration) -> None:
        self.slack = integration

    def connect_notion(self, integration: NotionIntegration) -> None:
        self.notion = integration

    def list_connected(self) -> list[str]:
        result = []
        if self.github:
            result.append("github")
        if self.gitlab:
            result.append("gitlab")
        if self.vscode:
            result.append("vscode")
        if self.discord:
            result.append("discord")
        if self.slack:
            result.append("slack")
        if self.notion:
            result.append("notion")
        return result
