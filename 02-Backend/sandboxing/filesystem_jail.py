import os
import pathlib


class FilesystemJail:
    def __init__(self, root: str):
        self.root = os.path.realpath(root)
        os.makedirs(self.root, exist_ok=True)

    def _is_under_root(self, resolved: str) -> bool:
        return resolved == self.root or resolved.startswith(self.root + os.sep)

    def reject_traversal(self, path: str) -> None:
        normalized = pathlib.Path(path).as_posix()
        if ".." in normalized.split("/"):
            raise ValueError("path traversal detected")
        if "\\" in normalized:
            raise ValueError("backslash traversal detected")

    def resolve_path(self, path: str) -> str:
        self.reject_traversal(path)
        joined = os.path.join(self.root, path)
        resolved = os.path.realpath(joined)
        if not self._is_under_root(resolved):
            raise PermissionError("path escapes jail root")
        return resolved

    def validate_symlink(self, link_path: str, target: str) -> None:
        link_resolved = os.path.realpath(os.path.join(self.root, link_path))
        target_resolved = os.path.realpath(target)
        if not self._is_under_root(target_resolved):
            raise PermissionError("symlink escape detected")
        if not self._is_under_root(link_resolved):
            raise PermissionError("symlink location outside jail")
