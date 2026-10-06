"""Docker container images for Astrovox."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DockerImage:
    """A Docker image definition."""
    name: str
    tag: str
    dockerfile: str
    context: str = "."

    def to_dict(self) -> dict:
        return {"name": self.name, "tag": self.tag, "dockerfile": self.dockerfile,
                "context": self.context}


class DockerImageBuilder:
    """Build Docker images."""

    def __init__(self):
        self.images: list[DockerImage] = []

    def define(self, name: str, tag: str, dockerfile: str, context: str = ".") -> DockerImage:
        img = DockerImage(name=name, tag=tag, dockerfile=dockerfile, context=context)
        self.images.append(img)
        return img

    def build_command(self, image: DockerImage) -> str:
        return (f"docker build -t {image.name}:{image.tag} "
                f"--file {image.dockerfile} {image.context}")

    def push_command(self, image: DockerImage) -> str:
        return f"docker push {image.name}:{image.tag}"

    def commands(self) -> list[str]:
        return [self.build_command(i) for i in self.images]

    def compose_file(self) -> str:
        return """version: '3.8'
services:
  astrovox-api:
    image: astrovox/api:latest
    ports:
      - "8080:8080"
"""
