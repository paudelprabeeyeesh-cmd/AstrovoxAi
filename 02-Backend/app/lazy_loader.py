from typing import TypeVar, Callable, Dict, Any, Optional, Generic
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LazyLoader(Generic[T]):
    def __init__(self, factory: Callable[[], T], cache: bool = True, ttl: Optional[float] = None):
        self._factory = factory
        self._cache = cache
        self._ttl = ttl
        self._value: Optional[T] = None
        self._loaded_at: Optional[float] = None
        self._loaded = False
        self._load_count = 0

    def get(self) -> T:
        if self._cache and self._loaded and self._value is not None:
            if self._ttl is None or (time.time() - self._loaded_at) < self._ttl:
                return self._value
        self._value = self._factory()
        self._loaded_at = time.time()
        self._loaded = True
        self._load_count += 1
        return self._value

    async def get_async(self) -> T:
        if self._cache and self._loaded and self._value is not None:
            if self._ttl is None or (time.time() - self._loaded_at) < self._ttl:
                return self._value
        result = self._factory()
        if asyncio.iscoroutine(result):
            result = await result
        self._value = result
        self._loaded_at = time.time()
        self._loaded = True
        self._load_count += 1
        return self._value

    def invalidate(self) -> None:
        self._loaded = False
        self._value = None
        self._loaded_at = None

    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_count(self) -> int:
        return self._load_count


def lazy(cache: bool = True, ttl: Optional[float] = None) -> Callable[[Callable[[], T]], LazyLoader[T]]:
    def decorator(factory: Callable[[], T]) -> LazyLoader[T]:
        return LazyLoader(factory, cache=cache, ttl=ttl)
    return decorator


class LazyModuleLoader:
    def __init__(self):
        self._modules: Dict[str, Any] = {}

    def register(self, name: str, factory: Callable[[], Any], cache: bool = True, ttl: Optional[float] = None) -> None:
        self._modules[name] = LazyLoader(factory, cache=cache, ttl=ttl)

    def get(self, name: str) -> Any:
        if name not in self._modules:
            raise KeyError(f"Lazy module '{name}' is not registered")
        return self._modules[name].get()

    async def get_async(self, name: str) -> Any:
        if name not in self._modules:
            raise KeyError(f"Lazy module '{name}' is not registered")
        return await self._modules[name].get_async()

    def invalidate(self, name: str) -> None:
        if name in self._modules:
            self._modules[name].invalidate()

    def invalidate_all(self) -> None:
        for loader in self._modules.values():
            loader.invalidate()

    def get_stats(self) -> Dict[str, int]:
        return {name: loader.load_count for name, loader in self._modules.items()}


_module_loader = LazyModuleLoader()


def register_lazy_module(name: str, factory: Callable[[], Any], cache: bool = True, ttl: Optional[float] = None) -> None:
    _module_loader.register(name, factory, cache=cache, ttl=ttl)


def get_lazy_module(name: str) -> Any:
    return _module_loader.get(name)


async def get_lazy_module_async(name: str) -> Any:
    return await _module_loader.get_async(name)


def invalidate_lazy_module(name: str) -> None:
    _module_loader.invalidate(name)


def invalidate_all_lazy_modules() -> None:
    _module_loader.invalidate_all()


def get_lazy_module_stats() -> Dict[str, int]:
    return _module_loader.get_stats()
