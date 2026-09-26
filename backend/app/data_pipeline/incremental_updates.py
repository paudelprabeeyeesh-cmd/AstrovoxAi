import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class IncrementalUpdateConfig:
    state_path: str = "./incremental_state.json"
    checksum_field: str = "id"
    watermark_field: str = "updated_at"
    batch_size: int = 512


class IncrementalUpdater:
    def __init__(self, config: Optional[IncrementalUpdateConfig] = None):
        self.config = config or IncrementalUpdateConfig()
        self.state: Dict[str, Any] = {}
        self._load_state()
        logger.info("Incremental updater initialized at %s", self.config.state_path)

    def _load_state(self) -> None:
        if os.path.exists(self.config.state_path):
            try:
                with open(self.config.state_path, "r") as f:
                    self.state = json.load(f)
            except Exception as exc:
                logger.warning("Failed to load incremental state: %s", exc)

    def _save_state(self) -> None:
        try:
            with open(self.config.state_path, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as exc:
            logger.warning("Failed to save incremental state: %s", exc)

    def _compute_checksum(self, record: Dict[str, Any]) -> str:
        raw = json.dumps(record, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _is_new_or_changed(self, record: Dict[str, Any]) -> bool:
        key = str(record.get(self.config.checksum_field, ""))
        checksum = self._compute_checksum(record)
        known = self.state.get(key)
        if known is None:
            return True
        return known.get("checksum") != checksum

    def filter_updates(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        new_records = []
        for record in records:
            if self._is_new_or_changed(record):
                key = str(record.get(self.config.checksum_field, ""))
                self.state[key] = {
                    "checksum": self._compute_checksum(record),
                    "updated_at": record.get(self.config.watermark_field),
                }
                new_records.append(record)
        self._save_state()
        return new_records

    def apply_incremental(self, existing: List[Dict[str, Any]], updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        index = {str(r.get(self.config.checksum_field, "")): r for r in existing}
        filtered = self.filter_updates(updates)
        for record in filtered:
            key = str(record.get(self.config.checksum_field, ""))
            index[key] = record
        return list(index.values())
