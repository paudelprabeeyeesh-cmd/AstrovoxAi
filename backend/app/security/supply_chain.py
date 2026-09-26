"""Supply-chain verification with SBOM, hash verification, and dependency integrity."""
import hashlib
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    TAMPERED = "tampered"
    MISSING = "missing"


@dataclass
class DependencyRecord:
    name: str
    version: str
    source: str
    hash_sha256: str
    verified_at: float = field(default_factory=time.time)
    status: VerificationStatus = VerificationStatus.UNVERIFIED


@dataclass
class SBOMEntry:
    component: str
    version: str
    purl: str
    licenses: List[str]
    verified: bool = False


class SupplyChainVerifier:
    def __init__(self):
        self._dependencies: Dict[str, DependencyRecord] = {}
        self._sbom: List[SBOMEntry] = []
        self._lock = __import__('threading').Lock()
        self._trusted_hashes: Dict[str, str] = {}

    def register_dependency(self, record: DependencyRecord):
        with self._lock:
            self._dependencies[record.name] = record

    def verify_artifact(self, path: str, expected_hash: Optional[str] = None) -> DependencyRecord:
        if not os.path.isfile(path):
            return DependencyRecord(name=os.path.basename(path), version="", source="", hash_sha256="", status=VerificationStatus.MISSING)
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        actual_hash = sha.hexdigest()
        expected = expected_hash or self._trusted_hashes.get(os.path.basename(path))
        status = VerificationStatus.VERIFIED if expected and actual_hash == expected else VerificationStatus.UNVERIFIED
        record = DependencyRecord(name=os.path.basename(path), version="", source=path, hash_sha256=actual_hash, status=status)
        with self._lock:
            self._dependencies[record.name] = record
        return record

    def add_sbom_entry(self, entry: SBOMEntry):
        with self._lock:
            self._sbom.append(entry)

    def get_sbom(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"component": e.component, "version": e.version, "purl": e.purl, "licenses": e.licenses, "verified": e.verified} for e in self._sbom]

    def verify_dependency(self, name: str, expected_hash: str) -> bool:
        with self._lock:
            dep = self._dependencies.get(name)
        if not dep:
            return False
        return dep.hash_sha256 == expected_hash

    def report(self) -> Dict[str, Any]:
        with self._lock:
            deps = list(self._dependencies.values())
            verified = sum(1 for d in deps if d.status == VerificationStatus.VERIFIED)
            tampered = sum(1 for d in deps if d.status == VerificationStatus.TAMPERED)
            missing = sum(1 for d in deps if d.status == VerificationStatus.MISSING)
        return {
            "total_dependencies": len(deps),
            "verified": verified,
            "tampered": tampered,
            "missing": missing,
            "sbom_entries": len(self._sbom),
        }


supply_chain_verifier = SupplyChainVerifier()
