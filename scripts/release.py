"""Release management utilities for Astrovox.

Provides helpers for version bumping, changelog generation, and release
artifact preparation.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: str = ""
    build: str = ""

    @classmethod
    def parse(cls, value: str) -> Version:
        match = re.match(r"^(\\d+)\\.(\\d+)\\.(\\d+)(?:-([^+]+))?(?:\\+(.+))?$", value)
        if not match:
            raise ValueError(f"Invalid version: {value}")
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=match.group(4) or "",
            build=match.group(5) or "",
        )

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += f"-{self.prerelease}"
        if self.build:
            base += f"+{self.build}"
        return base

    def bump_patch(self) -> Version:
        return Version(self.major, self.minor, self.patch + 1)

    def bump_minor(self) -> Version:
        return Version(self.major, self.minor + 1, 0)

    def bump_major(self) -> Version:
        return Version(self.major + 1, 0, 0)


@dataclass(frozen=True)
class ChangelogEntry:
    version: Version
    changes: Sequence[str]


def update_pyproject_version(version: Version, path: Path = Path("pyproject.toml")) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r'(?m)^(version\\s*=\\s*\")([^\"]+)(\")',
        lambda m: m.group(1) + str(version) + m.group(3),
        text,
    )
    path.write_text(text, encoding="utf-8")


def update_init_version(version: Version, path: Path = Path("astrovox/__init__.py")) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r'(?m)^(__version__\\s*=\\s*\")([^\"]+)(\")',
        lambda m: m.group(1) + str(version) + m.group(3),
        text,
    )
    path.write_text(text, encoding="utf-8")


def render_changelog(entries: Iterable[ChangelogEntry], path: Path = Path("CHANGELOG.md")) -> None:
    lines = ["# Changelog", ""]
    for entry in reversed(list(entries)):
        lines.append(f"## {entry.version}")
        lines.append("")
        for change in entry.changes:
            lines.append(f"- {change}")
        lines.append("")
    path.write_text("\\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    if len(argv or []) < 2:
        print("Usage: python scripts/release.py <bump_patch|bump_minor|bump_major|set:X.Y.Z>")
        return 1
    cmd = argv[1]
    base = Version.parse("1.0.0-rc1")
    try:
        if cmd == "bump_patch":
            new = base.bump_patch()
        elif cmd == "bump_minor":
            new = base.bump_minor()
        elif cmd == "bump_major":
            new = base.bump_major()
        elif cmd.startswith("set:"):
            new = Version.parse(cmd.split(":", 1)[1])
        else:
            print(f"Unknown command: {cmd}")
            return 1
    except ValueError as exc:
        print(str(exc))
        return 1
    update_pyproject_version(new)
    update_init_version(new)
    print(f"Updated version to {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
