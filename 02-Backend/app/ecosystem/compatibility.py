"""Compatibility Engine — verify API, version, dependency, security, and resource compatibility before activation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class VersionRequirement:
    min_version: str = "0.0.0"
    max_version: str = "999.999.999"
    exact_version: Optional[str] = None


@dataclass
class ResourceRequirement:
    min_memory_mb: int = 0
    min_cpu_cores: float = 0.0
    required_packages: Dict[str, VersionRequirement] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    max_startup_time_seconds: float = 30.0


@dataclass
class SecurityPolicy:
    allowed_permissions: List[str] = field(default_factory=list)
    denied_permissions: List[str] = field(default_factory=list)
    required_signatures: bool = False
    allowed_trust_levels: List[str] = field(default_factory=list)


@dataclass
class CompatibilityReport:
    compatible: bool
    api_compatible: bool
    version_compatible: bool
    dependencies_met: bool
    security_passed: bool
    resources_met: bool
    required_capabilities_met: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def parse_version(version: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in re.split(r"[.\-]", version)[:3] if part.isdigit())


def satisfies_version(actual: str, requirement: VersionRequirement) -> bool:
    if requirement.exact_version:
        return actual == requirement.exact_version
    actual_parts = parse_version(actual)
    min_parts = parse_version(requirement.min_version)
    max_parts = parse_version(requirement.max_version)
    if actual_parts < min_parts:
        return False
    if actual_parts > max_parts:
        return False
    return True


def satisfies_resource(actual: Dict[str, Any], requirement: ResourceRequirement) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    actual_memory = actual.get("memory_mb", 0)
    if actual_memory < requirement.min_memory_mb:
        issues.append(f"Insufficient memory: {actual_memory}MB < {requirement.min_memory_mb}MB")
    actual_cpu = actual.get("cpu_cores", 0.0)
    if actual_cpu < requirement.min_cpu_cores:
        issues.append(f"Insufficient CPU: {actual_cpu} < {requirement.min_cpu_cores}")
    actual_caps = set(actual.get("capabilities", []))
    missing = set(requirement.required_capabilities) - actual_caps
    if missing:
        issues.append(f"Missing capabilities: {sorted(missing)}")
    return len(issues) == 0, issues


def check_api_compatibility(entry_api: Dict[str, Any], current_api: Dict[str, Any]) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    entry_methods = set(entry_api.get("methods", []))
    current_methods = set(current_api.get("methods", []))
    missing_methods = entry_methods - current_methods
    if missing_methods:
        issues.append(f"Missing API methods: {sorted(missing_methods)}")
    entry_schemas = set(entry_api.get("schemas", []))
    current_schemas = set(current_api.get("schemas", []))
    missing_schemas = entry_schemas - current_schemas
    if missing_schemas:
        issues.append(f"Missing API schemas: {sorted(missing_schemas)}")
    return len(issues) == 0, issues


def check_dependencies(
    entry_dependencies: Dict[str, str],
    installed: Dict[str, str],
) -> Tuple[bool, List[str], List[str]]:
    issues: List[str] = []
    warnings: List[str] = []
    for name, required in entry_dependencies.items():
        actual = installed.get(name)
        if not actual:
            issues.append(f"Missing dependency: {name}")
            continue
        if required.startswith("^") or required.startswith("~"):
            operator = required[:1]
            version = required[1:]
            req = VersionRequirement(min_version=version)
            if not satisfies_version(actual, req):
                issues.append(f"Incompatible dependency {name}: {actual} does not satisfy {required}")
        elif re.match(r"^[0-9]+\.[0-9]+", required):
            if actual != required:
                warnings.append(f"Dependency {name} version mismatch: expected {required}, got {actual}")
    return len(issues) == 0, issues, warnings


def check_security_policy(
    entry: Any,
    policy: SecurityPolicy,
    registry: Any,
) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    entry_permissions = getattr(entry, "permissions", [])
    for denied in policy.denied_permissions:
        if denied in entry_permissions:
            issues.append(f"Entry requests denied permission: {denied}")
    for required in policy.allowed_permissions:
        if required not in entry_permissions:
            issues.append(f"Entry missing required permission: {required}")
    if policy.required_signatures and not getattr(entry, "signature", None):
        issues.append("Entry is missing required signature")
    if policy.allowed_trust_levels:
        entry_trust = getattr(entry, "trust_level", "").value
        if entry_trust not in policy.allowed_trust_levels:
            issues.append(f"Trust level {entry_trust} is not allowed")
    return len(issues) == 0, issues


def evaluate_compatibility(
    entry: Any,
    current_api: Dict[str, Any],
    installed_dependencies: Dict[str, str],
    available_resources: Dict[str, Any],
    security_policy: SecurityPolicy,
    registry: Any,
) -> CompatibilityReport:
    issues: List[str] = []
    warnings: List[str] = []

    api_compatible, api_issues = check_api_compatibility(
        getattr(entry, "api_spec", {}), current_api
    )
    issues.extend(api_issues)

    version_compatible = satisfies_version(
        getattr(entry, "version", "0.0.0"),
        VersionRequirement(min_version="0.0.0"),
    )

    deps_met, dep_issues, dep_warnings = check_dependencies(
        getattr(entry, "dependencies", {}), installed_dependencies
    )
    issues.extend(dep_issues)
    warnings.extend(dep_warnings)

    resources_met, resource_issues = satisfies_resource(
        available_resources,
        ResourceRequirement(**getattr(entry, "resource_requirements", {})),
    )
    issues.extend(resource_issues)

    security_passed, security_issues = check_security_policy(entry, security_policy, registry)
    issues.extend(security_issues)

    required_capabilities = getattr(entry, "capabilities", [])
    actual_capabilities = set(available_resources.get("capabilities", []))
    required_capabilities_met = set(required_capabilities).issubset(actual_capabilities)
    if not required_capabilities_met:
        missing = sorted(set(required_capabilities) - actual_capabilities)
        issues.append(f"Missing capabilities: {missing}")

    return CompatibilityReport(
        compatible=len(issues) == 0,
        api_compatible=api_compatible,
        version_compatible=version_compatible,
        dependencies_met=deps_met,
        security_passed=security_passed,
        resources_met=resources_met,
        required_capabilities_met=required_capabilities_met,
        issues=issues,
        warnings=warnings,
    )
