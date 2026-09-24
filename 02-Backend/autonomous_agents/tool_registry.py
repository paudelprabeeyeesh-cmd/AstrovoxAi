from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable[..., Any]] = field(default=None, repr=False, compare=False)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, name: str, description: str, parameters: Optional[Dict[str, Any]] = None, handler: Optional[Callable[..., Any]] = None) -> None:
        self._tools[name] = ToolSpec(name=name, description=description, parameters=parameters or {}, handler=handler)

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolSpec]:
        return list(self._tools.values())

    def call(self, name: str, **kwargs: Any) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool {name} not registered")
        if tool.handler is None:
            return f"mock:{name}"
        return tool.handler(**kwargs)

    def unregister(self, name: str) -> bool:
        return self._tools.pop(name, None) is not None
