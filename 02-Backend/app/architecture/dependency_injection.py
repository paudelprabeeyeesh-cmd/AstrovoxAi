"""Dependency injection container for AstrovoxAi."""

from typing import TypeVar, Optional, Type, Callable, Dict, Any
from dataclasses import dataclass

T = TypeVar("T")


class ServiceLifetime:
    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"


@dataclass
class ServiceDescriptor:
    service_type: Type[T]
    implementation: Optional[Type[T]] = None
    factory: Optional[Callable[[], T]] = None
    lifetime: str = ServiceLifetime.SINGLETON
    instance: Optional[T] = None


class DIContainer:
    _services: Dict[Type, ServiceDescriptor] = {}
    _scoped_instances: Dict[Type, Any] = {}

    @classmethod
    def register(
        cls,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        lifetime: str = ServiceLifetime.SINGLETON,
    ) -> None:
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation or service_type,
            factory=factory,
            lifetime=lifetime,
        )
        cls._services[service_type] = descriptor

    @classmethod
    def resolve(cls, service_type: Type[T]) -> Optional[T]:
        descriptor = cls._services.get(service_type)
        if not descriptor:
            return None

        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if descriptor.instance is None:
                descriptor.instance = cls._create_instance(descriptor)
            return descriptor.instance
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            if service_type not in cls._scoped_instances:
                cls._scoped_instances[service_type] = cls._create_instance(descriptor)
            return cls._scoped_instances[service_type]
        else:
            return cls._create_instance(descriptor)

    @classmethod
    def _create_instance(cls, descriptor: ServiceDescriptor) -> Any:
        if descriptor.factory:
            return descriptor.factory()
        if descriptor.implementation:
            return descriptor.implementation()
        return None

    @classmethod
    def clear_scope(cls) -> None:
        cls._scoped_instances.clear()

    @classmethod
    def reset(cls) -> None:
        cls._services.clear()
        cls._scoped_instances.clear()
