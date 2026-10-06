"""Kubernetes manifests for Astrovox."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class K8sManifest:
    """A Kubernetes manifest."""
    api_version: str
    kind: str
    name: str
    namespace: str = "astrovox"

    def to_yaml(self) -> str:
        return f"""apiVersion: {self.api_version}
kind: {self.kind}
metadata:
  name: {self.name}
  namespace: {self.namespace}
"""


class KubernetesSupport:
    """Kubernetes manifest generation."""

    def __init__(self):
        self.manifests: list[K8sManifest] = []

    def deployment(self, name: str, replicas: int = 3) -> K8sManifest:
        m = K8sManifest(api_version="apps/v1", kind="Deployment", name=name)
        self.manifests.append(m)
        return m

    def service(self, name: str) -> K8sManifest:
        m = K8sManifest(api_version="v1", kind="Service", name=name)
        self.manifests.append(m)
        return m

    def ingress(self, name: str) -> K8sManifest:
        m = K8sManifest(api_version="networking.k8s.io/v1", kind="Ingress", name=name)
        self.manifests.append(m)
        return m

    def all_manifests(self) -> str:
        return "\n---\n".join(m.to_yaml() for m in self.manifests)

    def helm_chart(self) -> str:
        return """apiVersion: v2
name: astrovox
description: Astrovox AI Platform
type: application
version: 1.0.0
"""
