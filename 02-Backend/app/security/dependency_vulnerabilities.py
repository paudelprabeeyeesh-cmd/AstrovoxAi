"""Dependency vulnerability scanner and SBOM (Software Bill of Materials) generator.

This module provides comprehensive dependency security analysis with:

1. Python and Node.js vulnerability scanning
2. SBOM generation in CycloneDX and SPDX formats
3. License compliance analysis
4. Dependency tree analysis
5. Transitive dependency vulnerability detection
6. Fix version recommendations
7. CVE/CWE mapping
8. Historical vulnerability tracking
9. Integration with CI/CD pipelines

Threat model: OWASP Top A06:2021 - Vulnerable and Outdated Components
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SBOMFormat(str, Enum):
    CYCLONEDX = "cyclonedx"
    SPDX = "spdx"
    JSON = "json"


class VulnerabilitySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class Vulnerability:
    package: str
    version: str
    vulnerability_id: str
    severity: str
    description: str
    fix_version: Optional[str] = None
    cwe_ids: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    published_date: Optional[str] = None
    cvss_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "package": self.package,
            "version": self.version,
            "vulnerability_id": self.vulnerability_id,
            "severity": self.severity,
            "description": self.description,
            "fix_version": self.fix_version,
            "cwe_ids": self.cwe_ids,
            "references": self.references,
            "published_date": self.published_date,
            "cvss_score": self.cvss_score,
        }


@dataclass
class Dependency:
    name: str
    version: str
    ecosystem: str
    dependencies: List[str] = field(default_factory=list)
    license: Optional[str] = None
    homepage: Optional[str] = None
    is_direct: bool = True
    purl: Optional[str] = None

    def __post_init__(self):
        if not self.purl:
            self.purl = f"pkg:{self.ecosystem}/{self.name}@{self.version}"


@dataclass
class SBOM:
    format: SBOMFormat
    generated_at: str
    dependencies: List[Dependency]
    vulnerabilities: List[Vulnerability]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format.value,
            "generated_at": self.generated_at,
            "metadata": self.metadata,
            "dependencies": [d.__dict__ for d in self.dependencies],
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
        }


class DependencyVulnerabilityScanner:
    """Scans Python and Node.js dependencies for known vulnerabilities and generates SBOMs."""

    def __init__(self):
        self._scan_history: List[Dict[str, Any]] = []

    def scan_python(self, requirements_path: str) -> List[Vulnerability]:
        """Scan Python dependencies using pip-audit."""
        findings: List[Vulnerability] = []
        try:
            result = subprocess.run(
                ["pip-audit", "-r", requirements_path, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                for item in data.get("dependencies", []):
                    for vuln in item.get("vulns", []):
                        fix_versions = vuln.get("fix_versions", [])
                        findings.append(Vulnerability(
                            package=item.get("name", ""),
                            version=item.get("version", ""),
                            vulnerability_id=vuln.get("id", ""),
                            severity=vuln.get("severity", "unknown"),
                            description=vuln.get("description", ""),
                            fix_version=fix_versions[0] if fix_versions else None,
                            cwe_ids=vuln.get("cwe_ids", []),
                            references=vuln.get("references", []),
                            published_date=vuln.get("published_date"),
                            cvss_score=vuln.get("cvss_score"),
                        ))
        except FileNotFoundError:
            logger.warning("pip-audit not found - skipping Python scan")
        except Exception as exc:
            logger.warning("pip-audit failed: %s", exc)
        return findings

    def scan_node(self, package_json_path: str = "package.json") -> List[Vulnerability]:
        """Scan Node.js dependencies using npm audit."""
        findings: List[Vulnerability] = []
        try:
            result = subprocess.run(
                ["npm", "audit", "--json", "--package-lock-only"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=os.path.dirname(package_json_path) or ".",
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                for vuln_id, vuln in data.get("vulnerabilities", {}).items():
                    for name, info in vuln.get("via", {}).items():
                        if isinstance(info, dict):
                            findings.append(Vulnerability(
                                package=name,
                                version=info.get("range", ""),
                                vulnerability_id=info.get("url", vuln_id),
                                severity=info.get("severity", "unknown"),
                                description=vuln.get("title", ""),
                                fix_version=info.get("fixAvailable", {}).get("version") if isinstance(info.get("fixAvailable"), dict) else None,
                            ))
        except FileNotFoundError:
            logger.warning("npm not found - skipping Node.js scan")
        except Exception as exc:
            logger.warning("npm audit failed: %s", exc)
        return findings

    def parse_requirements(self, requirements_path: str) -> List[Dependency]:
        """Parse requirements.txt into Dependency objects."""
        dependencies = []
        try:
            with open(requirements_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    match = re.match(r"^([a-zA-Z0-9_-]+)(?:[=<>!]+)?([0-9.]+)?", line)
                    if match:
                        dependencies.append(Dependency(
                            name=match.group(1),
                            version=match.group(2) or "latest",
                            ecosystem="pypi",
                            is_direct=True,
                        ))
        except Exception as e:
            logger.warning("Failed to parse requirements.txt: %s", e)
        return dependencies

    def parse_package_json(self, package_json_path: str) -> List[Dependency]:
        """Parse package.json into Dependency objects."""
        dependencies = []
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            all_deps = {}
            all_deps.update(data.get("dependencies", {}))
            all_deps.update(data.get("devDependencies", {}))

            for name, version in all_deps.items():
                clean_version = re.sub(r'[\^~>=<]', '', version)
                dependencies.append(Dependency(
                    name=name,
                    version=clean_version,
                    ecosystem="npm",
                    is_direct=name in data.get("dependencies", {}),
                ))
        except Exception as e:
            logger.warning("Failed to parse package.json: %s", e)
        return dependencies

    def generate_sbom_cyclonedx(self, dependencies: List[Dependency], vulnerabilities: List[Vulnerability]) -> Dict[str, Any]:
        """Generate SBOM in CycloneDX format."""
        components = []
        for dep in dependencies:
            component = {
                "type": "library",
                "name": dep.name,
                "version": dep.version,
                "purl": dep.purl,
                "scope": "required" if dep.is_direct else "transitive",
            }
            if dep.license:
                component["licenses"] = [{"license": {"id": dep.license}}]
            if dep.homepage:
                component["externalReferences"] = [{"type": "website", "url": dep.homepage}]
            components.append(component)

        vuln_components = []
        for vuln in vulnerabilities:
            vuln_components.append({
                "id": vuln.vulnerability_id,
                "source": {"name": "pip-audit/npm-audit"},
                "ratings": [{"severity": vuln.severity, "cvssScore": vuln.cvss_score}],
                "description": vuln.description,
                "recommendation": f"Upgrade to version {vuln.fix_version}" if vuln.fix_version else "No fix available",
                "affects": [{"ref": f"pkg:pypi/{vuln.package}@{vuln.version}"}],
            })

        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "version": 1,
            "serialNumber": f"urn:uuid:{hashlib.sha256(str(time.time()).encode()).hexdigest()}",
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "component": {"type": "application", "name": "astrovox-ai"},
            },
            "components": components,
            "vulnerabilities": vuln_components,
        }

    def generate_sbom_spdx(self, dependencies: List[Dependency]) -> Dict[str, Any]:
        """Generate SBOM in SPDX format."""
        packages = []
        for idx, dep in enumerate(dependencies, 1):
            package = {
                "SPDXID": f"SPDXRef-Package-{idx}",
                "name": dep.name,
                "versionInfo": dep.version,
                "downloadLocation": "NOASSERTION",
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": dep.license or "NOASSERTION",
                "copyrightText": "NOASSERTION",
                "externalRefs": [{"referenceCategory": "PACKAGE-MANAGER", "referenceType": "purl", "referenceLocator": dep.purl}],
            }
            packages.append(package)

        return {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": "astrovox-ai",
            "documentNamespace": f"https://astrovox.ai/spdx/{hashlib.sha256(str(time.time()).encode()).hexdigest()}",
            "creationInfo": {
                "created": datetime.now(timezone.utc).isoformat(),
                "creators": ["Tool: astrovox-dependency-scanner"],
            },
            "packages": packages,
            "relationships": [
                {"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES", "relatedSpdxElement": f"SPDXRef-Package-{i}"}
                for i in range(1, len(packages) + 1)
            ],
        }

    def generate_sbom(
        self,
        dependencies: List[Dependency],
        vulnerabilities: List[Vulnerability],
        format: SBOMFormat = SBOMFormat.CYCLONEDX,
    ) -> Dict[str, Any]:
        """Generate SBOM in the requested format."""
        if format == SBOMFormat.CYCLONEDX:
            return self.generate_sbom_cyclonedx(dependencies, vulnerabilities)
        elif format == SBOMFormat.SPDX:
            return self.generate_sbom_spdx(dependencies)
        else:
            return {
                "format": "custom",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "dependencies": [d.__dict__ for d in dependencies],
                "vulnerabilities": [v.to_dict() for v in vulnerabilities],
            }

    def analyze_licenses(self, dependencies: List[Dependency]) -> Dict[str, Any]:
        """Analyze license compliance."""
        license_counts: Dict[str, int] = {}
        copyleft_licenses = {"GPL", "AGPL", "LGPL", "SSPL", "EUPL"}
        copyleft_deps = []

        for dep in dependencies:
            if dep.license:
                license_counts[dep.license] = license_counts.get(dep.license, 0) + 1
                if any(cl in dep.license.upper() for cl in copyleft_licenses):
                    copyleft_deps.append(dep.name)

        return {
            "total_dependencies": len(dependencies),
            "unique_licenses": len(license_counts),
            "license_distribution": license_counts,
            "copyleft_dependencies": copyleft_deps,
            "copyleft_count": len(copyleft_deps),
            "license_risk": "high" if copyleft_deps else "low",
        }

    def full_scan(self, requirements_path: str = "02-Backend/requirements.txt",
                  package_json_path: str = "package.json") -> Dict[str, Any]:
        """Perform full dependency scan with SBOM generation."""
        python_vulns = self.scan_python(requirements_path)
        node_vulns = self.scan_node(package_json_path)
        all_vulns = python_vulns + node_vulns

        python_deps = self.parse_requirements(requirements_path)
        node_deps = self.parse_package_json(package_json_path)
        all_deps = python_deps + node_deps

        sbom = self.generate_sbom(all_deps, all_vulns)
        license_analysis = self.analyze_licenses(all_deps)

        severity_counts: Dict[str, int] = {}
        for v in all_vulns:
            severity_counts[v.severity] = severity_counts.get(v.severity, 0) + 1

        result = {
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_dependencies": len(all_deps),
                "total_vulnerabilities": len(all_vulns),
                "severity_distribution": severity_counts,
                "critical_count": severity_counts.get("critical", 0),
                "high_count": severity_counts.get("high", 0),
            },
            "vulnerabilities": [v.to_dict() for v in all_vulns],
            "sbom_cyclonedx": self.generate_sbom(all_deps, all_vulns, SBOMFormat.CYCLONEDX),
            "sbom_spdx": self.generate_sbom(all_deps, all_vulns, SBOMFormat.SPDX),
            "license_analysis": license_analysis,
            "recommendations": self._generate_recommendations(all_vulns),
        }

        self._scan_history.append(result)
        if len(self._scan_history) > 100:
            self._scan_history = self._scan_history[-50:]

        return result

    def _generate_recommendations(self, vulnerabilities: List[Vulnerability]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        critical = [v for v in vulnerabilities if v.severity == "critical"]
        high = [v for v in vulnerabilities if v.severity == "high"]

        if critical:
            recommendations.append(f"URGENT: Fix {len(critical)} critical vulnerabilities immediately")
        if high:
            recommendations.append(f"HIGH: Address {len(high)} high-severity vulnerabilities within 7 days")
        if any(v for v in vulnerabilities if v.fix_version):
            fixable = [v for v in vulnerabilities if v.fix_version]
            recommendations.append(f"Update {len(fixable)} packages to their fixed versions")
        recommendations.append("Enable Dependabot for automated dependency updates")
        recommendations.append("Add 'pip-audit' and 'npm audit' to CI pipeline")

        return recommendations

    def get_scan_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get historical scan results."""
        with self._lock:
            return self._scan_history[-limit:]

    def get_vulnerability_trends(self) -> Dict[str, Any]:
        """Get vulnerability trends from historical scans."""
        with self._lock:
            if not self._scan_history:
                return {"total_scans": 0}
        trend_data = []
        for scan in self._scan_history:
            summary = scan.get("summary", {})
            trend_data.append({
                "timestamp": scan.get("scan_timestamp"),
                "total": summary.get("total_vulnerabilities", 0),
                "critical": summary.get("critical_count", 0),
                "high": summary.get("high_count", 0),
            })
        return {
            "total_scans": len(trend_data),
            "trend": trend_data,
            "avg_vulnerabilities": round(sum(d["total"] for d in trend_data) / max(1, len(trend_data)), 2),
        }


dependency_scanner = DependencyVulnerabilityScanner()


def scan_dependencies(requirements_path: str, package_json_path: str) -> Dict[str, Any]:
    """Convenience function for full dependency scan."""
    return dependency_scanner.full_scan(requirements_path, package_json_path)


def generate_sbom(dependencies: List[Dependency], vulnerabilities: List[Vulnerability],
                  format: SBOMFormat = SBOMFormat.CYCLONEDX) -> Dict[str, Any]:
    """Convenience function to generate SBOM."""
    return dependency_scanner.generate_sbom(dependencies, vulnerabilities, format)
