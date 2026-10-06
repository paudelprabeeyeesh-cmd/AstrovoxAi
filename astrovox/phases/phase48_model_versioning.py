"""Semantic versioning for models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelVersion:
    """A model version specifier."""
    major: int = 0
    minor: int = 0
    patch: int = 0
    prerelease: str = ""

    def __str__(self) -> str:
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            s += f"-{self.prerelease}"
        return s

    @classmethod
    def parse(cls, v: str) -> "ModelVersion":
        pre = ""
        if "-" in v:
            v, pre = v.split("-", 1)
        parts = v.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return cls(major=major, minor=minor, patch=patch, prerelease=pre)

    def bump_major(self) -> "ModelVersion":
        return ModelVersion(self.major + 1, 0, 0, self.prerelease)

    def bump_minor(self) -> "ModelVersion":
        return ModelVersion(self.major, self.minor + 1, 0, self.prerelease)

    def bump_patch(self) -> "ModelVersion":
        return ModelVersion(self.major, self.minor, self.patch + 1, self.prerelease)

    def is_newer_than(self, other: "ModelVersion") -> bool:
        t = (self.major, self.minor, self.patch)
        o = (other.major, other.minor, other.patch)
        return t > o

    def satisfies(self, spec: str) -> bool:
        """Check if version satisfies a constraint like >=1.2.0."""
        if spec.startswith(">="):
            req = ModelVersion.parse(spec[2:])
            return self.is_newer_than(req) or self.major == req.major and self.minor == req.minor and self.patch == req.patch
        if spec.startswith("~="):
            req = ModelVersion.parse(spec[2:])
            return self.major == req.major and self.minor == req.minor
        return True
