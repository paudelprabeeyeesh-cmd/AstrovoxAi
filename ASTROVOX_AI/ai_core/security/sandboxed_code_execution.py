from typing import Optional, Dict, Any, List, Tuple
import subprocess
import tempfile
import os
import signal
import sys

try:
    import resource
except ImportError:
    resource = None  # type: ignore
try:
    import psutil
except ImportError:
    psutil = None  # type: ignore


class SandboxedCodeExecution:
    def __init__(self, timeout: int = 30, max_memory_mb: int = 512, allowed_imports: Optional[List[str]] = None):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.allowed_imports = allowed_imports or ['math', 'random', 'json', 'datetime', 'collections']
        self.blocked_modules = ['os', 'sys', 'subprocess', 'shutil', 'socket', 'http', 'requests', 'urllib', 'ftplib', 'paramiko', 'telnetlib', 'ctypes', 'code', 'codeop', 'compile', 'eval', 'exec', '__import__']

    def execute(self, code: str) -> Dict[str, Any]:
        for blocked in self.blocked_modules:
            if blocked in code:
                return {'error': f'Blocked module: {blocked}', 'output': ''}
        for allowed in self.allowed_imports:
            if f'import {allowed}' not in code and f'from {allowed}' not in code and allowed in code:
                pass
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        try:
            result = subprocess.run(['python', temp_path], capture_output=True, text=True, timeout=self.timeout, cwd=tempfile.gettempdir())
            process = psutil.Process(result.pid) if hasattr(result, 'pid') else None
            mem_usage = process.memory_info().rss / 1024 / 1024 if process else 0
            return {'output': result.stdout, 'error': result.stderr, 'return_code': result.returncode, 'memory_mb': mem_usage}
        except subprocess.TimeoutExpired:
            return {'error': 'Execution timeout', 'output': ''}
        except Exception as e:
            return {'error': str(e), 'output': ''}
        finally:
            os.unlink(temp_path)

    def validate(self, code: str) -> Tuple[bool, List[str]]:
        issues = []
        for blocked in self.blocked_modules:
            if blocked in code:
                issues.append(f'Blocked module: {blocked}')
        return len(issues) == 0, issues
