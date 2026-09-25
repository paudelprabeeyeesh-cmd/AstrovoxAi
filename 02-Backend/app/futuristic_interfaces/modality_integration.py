import logging
from typing import Any

logger = logging.getLogger(__name__)


class ModalityIntegrationService:
    MODALITY_CONFIG = {
        "eeg": {"unit": "uV", "typical_range": (-100, 100), "impedance_unit": "kOhm"},
        "emg": {"unit": "mV", "typical_range": (-5, 5), "impedance_unit": "kOhm"},
        "meg": {"unit": "fT", "typical_range": (-200, 200), "impedance_unit": "N/A"},
    }

    def __init__(self) -> None:
        self._statuses: dict[str, dict[str, Any]] = {}

    def acquire(self, modality: str, channels: list[str], sample_rate_hz: float) -> dict[str, Any]:
        config = self.MODALITY_CONFIG.get(modality.lower(), self.MODALITY_CONFIG["eeg"])
        acquisition_id = f"{modality}_{len(self._statuses)}"
        self._statuses[acquisition_id] = {
            "modality": modality,
            "channels": channels,
            "sample_rate_hz": sample_rate_hz,
            "status": "acquiring",
            "unit": config["unit"],
        }
        return {
            "acquisition_id": acquisition_id,
            "modality": modality,
            "channels": channels,
            "sample_rate_hz": sample_rate_hz,
            "unit": config["unit"],
            "typical_range": config["typical_range"],
            "impedance_unit": config["impedance_unit"],
        }

    def get_status(self, modality: str) -> dict[str, Any]:
        items = [v for v in self._statuses.values() if v["modality"] == modality]
        return {
            "modality": modality,
            "active_acquisitions": len(items),
            "acquisitions": items,
        }
