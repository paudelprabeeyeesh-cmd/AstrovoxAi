"""Extension loader for phases 31-70."""
from typing import Any, Dict, List
from extensions.framework.phase_31_70 import EXTENSIONS


class ExtensionLoader:
    def __init__(self):
        self._extensions: Dict[int, Any] = {ext.phase: ext for ext in EXTENSIONS}

    def load(self, phase: int) -> Any:
        return self._extensions.get(phase)

    def load_all(self) -> List[Any]:
        return list(self._extensions.values())

    def initialize_all(self) -> None:
        for ext in self._extensions.values():
            ext.initialize()

    def get_status(self) -> Dict[str, Any]:
        return {
            "loaded": len(self._extensions),
            "phases": list(self._extensions.keys()),
        }


loader = ExtensionLoader()
