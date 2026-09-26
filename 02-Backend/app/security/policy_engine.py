"""Policy Engine with OPA integration."""

from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum
import json
import subprocess
import tempfile
import os


class PolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class PolicyInput:
    user: Dict[str, Any]
    resource: Dict[str, Any]
    action: str
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


class PolicyEngine:
    _policies: Dict[str, str] = {}

    @classmethod
    def load_policy(cls, name: str, rego_policy: str) -> None:
        cls._policies[name] = rego_policy

    @classmethod
    def evaluate(cls, policy_name: str, input_data: PolicyInput) -> PolicyDecision:
        policy = cls._policies.get(policy_name)
        if not policy:
            return PolicyDecision.DENY
        with tempfile.TemporaryDirectory() as tmpdir:
            policy_file = os.path.join(tmpdir, "policy.rego")
            with open(policy_file, "w") as f:
                f.write(policy)
            data_file = os.path.join(tmpdir, "input.json")
            with open(data_file, "w") as f:
                json.dump(input_data.__dict__, f)
            try:
                result = subprocess.run(
                    ["opa", "eval", "--data", policy_file, "--input", data_file, "--format", "raw"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    output = json.loads(result.stdout)
                    if output and output[0].get("result") == PolicyDecision.ALLOW.value:
                        return PolicyDecision.ALLOW
            except Exception:
                pass
        return PolicyDecision.DENY

    @classmethod
    def evaluate_local(cls, policy_name: str, input_data: PolicyInput) -> PolicyDecision:
        policy = cls._policies.get(policy_name)
        if not policy:
            return PolicyDecision.DENY
        if "admin" in input_data.user.get("roles", []):
            return PolicyDecision.ALLOW
        return PolicyDecision.DENY


DEFAULT_POLICIES = {
    "default": """
        package astrovox.authz
        default allow = false
        allow {
            input.user.roles[_] == "admin"
        }
        allow {
            input.user.id == input.resource.owner_id
            input.action == "read"
        }
    """,
}

for name, policy in DEFAULT_POLICIES.items():
    PolicyEngine.load_policy(name, policy)
