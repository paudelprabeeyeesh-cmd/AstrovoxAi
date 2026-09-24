import ast
from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass
class PermissionProfile:
    allowed_imports: Set[str]
    allowed_builtins: Set[str]
    max_execution_time: float
    max_memory_mb: int


class PermissionChecker:
    DEFAULT_ALLOWED_BUILTINS = {
        "abs", "all", "any", "bool", "dict", "enumerate",
        "float", "int", "len", "list", "max", "min",
        "print", "range", "sorted", "str", "sum", "tuple",
    }

    def __init__(self, profile: PermissionProfile):
        self.profile = profile

    def check_imports(self, code: str) -> List[str]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []
        blocked = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split(".")[0]
                    if name not in self.profile.allowed_imports:
                        blocked.append(name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    name = node.module.split(".")[0]
                    if name not in self.profile.allowed_imports:
                        blocked.append(name)
        return blocked

    def check_operation(self, operation: str) -> bool:
        disallowed = {"os", "sys", "subprocess", "shutil", "socket", "http"}
        return not any(token in operation for token in disallowed)

    def apply(self, code: str) -> bool:
        blocked_imports = self.check_imports(code)
        return len(blocked_imports) == 0
