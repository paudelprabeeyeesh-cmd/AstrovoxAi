from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class ActionResult:
    tool_name: str
    result: Any
    error: Optional[str] = None
    timed_out: bool = False


class ActionExecutor:
    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def execute(self, action: str, args: Dict[str, Any], tools: Dict[str, Callable]) -> ActionResult:
        if action not in tools:
            return ActionResult(tool_name=action, result=None, error=f"Unknown tool: {action}")
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(tools[action], **args)
                result = future.result(timeout=self.timeout)
            return ActionResult(tool_name=action, result=result)
        except TimeoutError:
            return ActionResult(tool_name=action, result=None, error="Timeout", timed_out=True)
        except Exception as e:  # noqa: BLE001
            return ActionResult(tool_name=action, result=None, error=str(e))
