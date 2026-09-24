from typing import List, Dict, Optional


class PatchResult:
    def __init__(self, file_path: str, success: bool, content: str = "", error: str = ""):
        self.file_path = file_path
        self.success = success
        self.content = content
        self.error = error


class AtomicMultiFileTransaction:
    def __init__(self):
        self.patches: Dict[str, str] = {}
        self.originals: Dict[str, str] = {}
        self.committed: bool = False
        self.rolled_back: bool = False

    def stage(self, file_path: str, original: str, patched: str) -> None:
        self.originals[file_path] = original
        self.patches[file_path] = patched

    def commit(self, validators: Optional[List] = None) -> List[PatchResult]:
        if self.committed:
            raise RuntimeError("Transaction already committed")
        if self.rolled_back:
            raise RuntimeError("Transaction rolled back")
        results = []
        all_valid = True
        for file_path, patched in self.patches.items():
            result = PatchResult(file_path=file_path, success=True, content=patched)
            if validators:
                for validator in validators:
                    try:
                        validation = validator(patched)
                    except TypeError:
                        validation = validator(patched, self.originals[file_path])
                    if not validation.get("valid", True):
                        result.success = False
                        result.error = "; ".join(validation.get("errors", ["validation failed"]))
                        all_valid = False
                        break
            results.append(result)
        if all_valid:
            self.committed = True
        else:
            self.rollback()
            for result in results:
                if not result.success:
                    result.error = f"Transaction rolled back: {result.error}"
        return results

    def rollback(self) -> None:
        self.patches.clear()
        if not self.committed:
            self.rolled_back = True

    def get_staged_files(self) -> List[str]:
        return list(self.patches.keys())

    def is_committed(self) -> bool:
        return self.committed

    def is_rolled_back(self) -> bool:
        return self.rolled_back
