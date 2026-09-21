import logging
import os
import subprocess
import tempfile
import time
from typing import Any

logger = logging.getLogger(__name__)


class CodeAgent:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.symbol_index = {}
        self.call_graph = {}
        self.dependency_graph = {}

    def index_repo(self) -> dict:
        if not os.path.isdir(self.repo_path):
            return {"error": "Repository not found"}
        files_indexed = 0
        symbols_found = 0
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", "__pycache__", "dist", "build")]
            for fname in files:
                if fname.endswith((".py", ".ts", ".js", ".rs", ".go", ".java")):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        rel = os.path.relpath(fpath, self.repo_path)
                        self.symbol_index[rel] = self._extract_symbols(content, fpath)
                        symbols_found += len(self.symbol_index[rel])
                        files_indexed += 1
                    except Exception as e:
                        logger.warning(f"Failed to index {fpath}: {e}")
        return {
            "repo_path": self.repo_path,
            "files_indexed": files_indexed,
            "symbols_found": symbols_found,
        }

    def _extract_symbols(self, content: str, file_path: str) -> list[dict]:
        symbols = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("function ") or stripped.startswith("class ") or stripped.startswith("export "):
                name = stripped.split("(")[0].split(" ")[-1].strip()
                symbols.append({
                    "name": name,
                    "line": i,
                    "file": file_path,
                    "signature": stripped[:200],
                })
        return symbols

    def find_references(self, symbol_name: str) -> list[dict]:
        results = []
        for file_path, symbols in self.symbol_index.items():
            for sym in symbols:
                if symbol_name.lower() in sym["name"].lower():
                    results.append({**sym, "file": file_path})
        return results

    def get_symbol(self, symbol_name: str) -> dict | None:
        refs = self.find_references(symbol_name)
        if not refs:
            return None
        definitions = [r for r in refs if r["name"] == symbol_name]
        return definitions[0] if definitions else refs[0]

    def read_file(self, file_path: str, offset: int = 1, limit: int = 200) -> str:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            start = max(0, offset - 1)
            end = min(len(lines), start + limit)
            return "".join(lines[start:end])
        except Exception as e:
            return f"Error: {e}"

    def edit_file(self, file_path: str, old_string: str, new_string: str) -> dict:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            if old_string not in content:
                return {"success": False, "error": "old_string not found"}
            new_content = content.replace(old_string, new_string, 1)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return {"success": True, "file": file_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_command(self, command: str, timeout: int = 30) -> dict:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:10000],
                "stderr": result.stderr[:10000],
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_tests(self, test_path: str = "tests") -> dict:
        return self.run_command(f"python -m pytest {test_path} -x --tb=short", timeout=120)

    def git_status(self) -> dict:
        return self.run_command("git status --porcelain")

    def git_diff(self) -> dict:
        result = self.run_command("git diff")
        if result.get("success"):
            return {"diff": result.get("stdout", "")}
        return result

    def git_commit(self, message: str) -> dict:
        return self.run_command(f'git add -A && git commit -m "{message}"')

    def verify_syntax(self, file_path: str) -> dict:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            if file_path.endswith(".py"):
                compile(content, full_path, "exec")
                return {"success": True, "file": file_path, "status": "syntax_ok"}
            elif file_path.endswith(".ts"):
                result = self.run_command(f"npx tsc --noEmit {full_path}", timeout=30)
                return {"success": result.get("success", False), "file": file_path, "status": "ts_check", "output": result.get("stdout", "")}
            else:
                return {"success": True, "file": file_path, "status": "unknown_format_skipped"}
        except SyntaxError as e:
            return {"success": False, "file": file_path, "error": f"Syntax error: {e}"}
        except Exception as e:
            return {"success": False, "file": file_path, "error": str(e)}

    def create_checkpoint(self, message: str) -> dict:
        result = self.git_commit(message)
        return {
            "success": result.get("success", False),
            "message": message,
            "output": result.get("stdout", ""),
            "error": result.get("stderr", ""),
        }
