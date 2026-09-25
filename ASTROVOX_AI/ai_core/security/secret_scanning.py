from typing import Optional, Dict, Any, List, Tuple
import re
import os


class SecretScanner:
    def __init__(self):
        self.patterns = {
            'api_key': r'(?i)api[_-]?key[\s:=]+[\'"]?([A-Za-z0-9_\-]{20,})[\'"]?',
            'secret': r'(?i)secret[\s:=]+[\'"]?([A-Za-z0-9_\-]{20,})[\'"]?',
            'password': r'(?i)password[\s:=]+[\'"]?([^\'"]{8,})[\'"]?',
            'token': r'(?i)token[\s:=]+[\'"]?([A-Za-z0-9_\-\.]{20,})[\'"]?',
            'private_key': r'-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----',
            'aws_access_key': r'(?i)AKIA[0-9A-Z]{16}',
            'github_token': r'ghp_[A-Za-z0-9_]{36}',
            'slack_token': r'xox[baprs]-[0-9a-zA-Z-]+',
        }
        self.compiled_patterns = {k: re.compile(v) for k, v in self.patterns.items()}
        self.findings: List[Dict[str, Any]] = []

    def scan_text(self, text: str, source: str = 'unknown') -> List[Dict[str, Any]]:
        findings = []
        for secret_type, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                finding = {'type': secret_type, 'source': source, 'match': match.group(0), 'start': match.start(), 'end': match.end(), 'severity': 'high'}
                findings.append(finding)
                self.findings.append(finding)
        return findings

    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            return []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return self.scan_text(content, file_path)

    def scan_directory(self, directory: str, extensions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        all_findings = []
        extensions = extensions or ['.py', '.js', '.ts', '.json', '.yaml', '.yml', '.env', '.txt', '.md']
        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    findings = self.scan_file(os.path.join(root, file))
                    all_findings.extend(findings)
        return all_findings

    def redact(self, text: str) -> str:
        for pattern in self.compiled_patterns.values():
            text = pattern.sub('[REDACTED]', text)
        return text
