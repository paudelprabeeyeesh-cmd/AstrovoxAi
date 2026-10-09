import hashlib
from dataclasses import dataclass
from typing import List, Optional

from backup_recovery.snapshot_manager import Snapshot
from backup_recovery.incremental_backup import IncrementalBackup


@dataclass
class VerificationResult:
    verified: bool
    message: str
    details: dict = None


class BackupVerifier:
    @staticmethod
    def verify_snapshot(
        snapshot: Snapshot,
        expected_data: bytes,
    ) -> VerificationResult:
        if snapshot.size_bytes != len(expected_data):
            return VerificationResult(
                verified=False,
                message="Snapshot size mismatch",
                details={
                    "expected_size": len(expected_data),
                    "actual_size": snapshot.size_bytes,
                },
            )
        expected_checksum = hashlib.sha256(expected_data).hexdigest()
        if snapshot.checksum != expected_checksum:
            return VerificationResult(
                verified=False,
                message="Snapshot checksum mismatch",
                details={
                    "expected_checksum": expected_checksum,
                    "actual_checksum": snapshot.checksum,
                },
            )
        return VerificationResult(
            verified=True,
            message="Snapshot is valid",
            details={
                "backup_id": snapshot.backup_id,
                "size_bytes": snapshot.size_bytes,
            },
        )

    @staticmethod
    def verify_incremental_backup(
        backup: IncrementalBackup,
    ) -> VerificationResult:
        if backup.end_time is None:
            return VerificationResult(
                verified=False,
                message="Incremental backup not completed",
                details={"backup_id": backup.backup_id},
            )
        total_size = sum(len(c) for c in backup.changes)
        if backup.metadata.get("total_size") != total_size:
            return VerificationResult(
                verified=False,
                message="Incremental backup size metadata mismatch",
                details={
                    "expected_size": total_size,
                    "actual_size": backup.metadata.get("total_size"),
                },
            )
        if backup.metadata.get("change_count") != len(backup.changes):
            return VerificationResult(
                verified=False,
                message="Incremental backup change count metadata mismatch",
                details={
                    "expected_count": len(backup.changes),
                    "actual_count": backup.metadata.get("change_count"),
                },
            )
        return VerificationResult(
            verified=True,
            message="Incremental backup is valid",
            details={
                "backup_id": backup.backup_id,
                "change_count": len(backup.changes),
            },
        )

    @staticmethod
    def verify_checksum(data: bytes, expected_checksum: str) -> VerificationResult:
        actual_checksum = hashlib.sha256(data).hexdigest()
        if actual_checksum != expected_checksum:
            return VerificationResult(
                verified=False,
                message="Checksum mismatch",
                details={
                    "expected": expected_checksum,
                    "actual": actual_checksum,
                },
            )
        return VerificationResult(
            verified=True,
            message="Checksum is valid",
            details={"checksum": actual_checksum},
        )
