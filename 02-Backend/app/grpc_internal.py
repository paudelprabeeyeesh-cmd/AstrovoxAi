"""gRPC internal service definitions."""

from typing import Optional
from dataclasses import dataclass


@dataclass
class GRPCService:
    name: str
    port: int
    proto_file: str
    dependencies: list[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class GRPCServer:
    _services: Dict[str, GRPCService] = {}

    @classmethod
    def register(cls, service: GRPCService) -> None:
        cls._services[service.name] = service

    @classmethod
    def get(cls, name: str) -> Optional[GRPCService]:
        return cls._services.get(name)

    @classmethod
    def list_services(cls) -> list[str]:
        return list(cls._services.keys())


INTERNAL_SERVICES = [
    GRPCService("model-gateway", 50051, "model_gateway.proto", ["redis", "postgres"]),
    GRPCService("memory-coordinator", 50052, "memory_coordinator.proto", ["redis", "vector"]),
    GRPCService("agent-orchestrator", 50053, "agent_orchestrator.proto", ["redis", "queue"]),
    GRPCService("billing-coordinator", 50054, "billing_coordinator.proto", ["postgres"]),
    GRPCService("notification-dispatcher", 50055, "notification_dispatcher.proto", ["queue"]),
]

for svc in INTERNAL_SERVICES:
    GRPCServer.register(svc)
