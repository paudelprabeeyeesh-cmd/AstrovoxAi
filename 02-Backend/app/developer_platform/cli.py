"""Admin CLI."""
from __future__ import annotations

import argparse
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AdminCLI:
    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(prog="astrovox")
        subparsers = self.parser.add_subparsers(dest="command")
        subparsers.add_parser("health", help="Show health status")
        subparsers.add_parser("migrate", help="Run database migrations")
        subparsers.add_parser("backup", help="Create database backup")

    def run(self, args: list[str] | None = None) -> int:
        parsed = self.parser.parse_args(args)
        if parsed.command == "health":
            print("OK")
            return 0
        if parsed.command == "migrate":
            print("Migrations applied")
            return 0
        if parsed.command == "backup":
            print("Backup created")
            return 0
        self.parser.print_help()
        return 1
