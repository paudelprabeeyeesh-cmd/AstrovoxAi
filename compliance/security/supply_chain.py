"""Supply chain compliance checks."""
from typing import Any, Dict, List
from ..policy_engine import PolicyEngine
from ..compliance_logger import ComplianceLogger


class SupplyChainCompliance:
    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.logger = ComplianceLogger("supply_chain")

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        checks = {
            "sbom_maintained": self._check_sbom(context),
            "artifact_signing": self._check_signing(context),
            "dependency_verification": self._check_dependencies(context),
        }
        passed = sum(1 for v in checks.values() if v.get("pass"))
        self.logger.log_event("supply_chain_evaluation", {"checks": checks, "passed": passed, "total": len(checks)})
        return {"framework": "supply_chain", "checks": checks, "passed": passed, "total": len(checks), "score": round(passed / len(checks), 3) if checks else 0.0}

    def _check_sbom(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        result = {"pass": bool(ctx.get("sbom")), "control": "SC-SBOM-1"}
        if not result["pass"]:
            result["remediation"] = "Maintain a Software Bill of Materials"
        return result

    def _check_signing(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        result = {"pass": bool(ctx.get("artifact_signing")), "control": "SC-SIGN-1"}
        if not result["pass"]:
            result["remediation"] = "Sign all build artifacts with verified keys"
        return result

    def _check_dependencies(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        result = {"pass": bool(ctx.get("dependency_verification")), "control": "SC-DEP-1"}
        if not result["pass"]:
            result["remediation"] = "Verify dependency hashes before installation"
        return result


supply_chain_compliance = SupplyChainCompliance()
