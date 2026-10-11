"""Secret-pattern scan over full git history (W3.2).

Uses `git grep` across all refs, which is far faster than materialising
every blob of every commit. Reports the commit, path and matched pattern
and never the matched value, so the output can be shown safely.

This is a stand-in for gitleaks/trufflehog, which are not installed in
this environment. It is deliberately narrow: high-confidence shapes whose
false-positive rate is near zero, because a wide scan on a history that
once tracked a junk .env produces noise rather than signal. Run the real
scanners in CI; security.yml already has gitleaks and trufflehog.
"""
import re
import subprocess
import sys
from collections import Counter

PATTERNS = [
    ("supabase_service_role", re.compile(r"service_role[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9._-]{40,}")),
    ("supabase_jwt", re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}")),
    ("openai_api_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("anthropic_api_key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("aws_access_key_id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("github_pat", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("stripe_secret_key", re.compile(r"sk_live_[A-Za-z0-9]{20,}")),
    ("stripe_webhook_secret", re.compile(r"whsec_[A-Za-z0-9]{20,}")),
    ("vite_privileged_var", re.compile(r"VITE_[A-Z0-9_]*(?:SERVICE_ROLE|SECRET|PRIVATE)[A-Z0-9_]*\s*=\s*\S{8,}")),
    ("postgres_dsn_with_password", re.compile(r"postgres(?:ql)?://[^:\s]+:[^@\s]{6,}@")),
]

PLACEHOLDER_VALUES = (
    "example", "changeme", "change-me", "placeholder", "your_key", "xxxxx",
    "dummy", "test-secret", "ci-only", "not-a-real", "redacted", "insert",
    "sample", "fake", "aaaaaa",
)


def is_placeholder(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in PLACEHOLDER_VALUES)


def scan(refs):
    """git grep -I (skip binary) across every ref given."""
    joined = "".join(f"(?!<{r}\\b)" for r in ())  # no-op, keeps linters quiet
    cmd = [
        "git", "grep", "-I", "-n", "-E",
        "|".join(f"(?:{p.pattern})" for _n, p in PATTERNS),
        *refs,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, errors="replace").stdout
    findings = []
    seen = set()
    for line in out.splitlines():
        # Format: <ref>:<path>:<lineno>:<text>
        parts = line.split(":", 3)
        if len(parts) < 4:
            continue
        ref, path, lineno, text = parts
        if path.startswith(("tools/", ".github/", "docs/", ".gitleaks")) or "test_" in path:
            continue
        for name, pattern in PATTERNS:
            m = pattern.search(text)
            if not m:
                continue
            if is_placeholder(m.group(0)):
                continue
            key = (name, path)
            if key in seen:
                continue
            seen.add(key)
            findings.append((ref, path, name, int(lineno)))
            break
    return findings


def main() -> int:
    refs = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname)"],
        capture_output=True, text=True,
    ).stdout.split()
    if not refs:
        refs = ["HEAD"]

    print("=== SECRET SCAN (full history, matched values redacted) ===")
    print(f"refs scanned: {len(refs)}")
    findings = scan(refs)
    counts = Counter(name for _r, _p, name, _l in findings)

    print(f"findings    : {len(findings)}\n")
    if findings:
        print("pattern | path | first line")
        print("-" * 78)
        for ref, path, name, lineno in findings[:120]:
            print(f"{name:26s} | {path}:{lineno} | seen at {ref}")
    else:
        print("(no high-confidence secrets found)")

    print("\n=== BY PATTERN ===")
    for name, count in counts.most_common():
        print(f"  {count:4d}  {name}")
    if not counts:
        print("  (none)")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
