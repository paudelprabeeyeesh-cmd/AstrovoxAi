import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ModalityAcquisition:
    acquisition_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    modality: str = "eeg"
    channels: list[str] = field(default_factory=list)
    sample_rate_hz: float = 250.0
    unit: str = "uV"
    typical_range: tuple[float, float] = (-100.0, 100.0)
    impedance_unit: str = "kOhm"
    status: str = "acquiring"
    started_at: float = field(default_factory=time.time)


class ModalityIntegrationService:
    MODALITY_CONFIG = {
        "eeg": {"unit": "uV", "typical_range": (-100, 100), "impedance_unit": "kOhm", "default_channels": ["FP1", "FP2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2", "Fz", "Cz", "Pz", "Oz"]},
        "emg": {"unit": "mV", "typical_range": (-5, 5), "impedance_unit": "kOhm", "default_channels": ["EMG1", "EMG2", "EMG3", "EMG4"]},
        "meg": {"unit": "fT", "typical_range": (-200, 200), "impedance_unit": "N/A", "default_channels": ["MEG1", "MEG2", "MEG3", "MEG4", "MEG5", "MEG6"]},
        "eog": {"unit": "uV", "typical_range": (-50, 50), "impedance_unit": "kOhm", "default_channels": ["EOG1", "EOG2"]},
        "ecg": {"unit": "mV", "typical_range": (-5, 5), "impedance_unit": "kOhm", "default_channels": ["ECG1", "ECG2"]},
    }

    def __init__(self) -> None:
        self._acquisitions: dict[str, ModalityAcquisition] = {}

    def acquire(self, modality: str, channels: list[str], sample_rate_hz: float) -> dict[str, Any]:
        config = self.MODALITY_CONFIG.get(modality.lower(), self.MODALITY_CONFIG["eeg"])
        acquisition = ModalityAcquisition(
            modality=modality,
            channels=channels or config["default_channels"],
            sample_rate_hz=sample_rate_hz,
            unit=config["unit"],
            typical_range=tuple(config["typical_range"]),
            impedance_unit=config["impedance_unit"],
        )
        self._acquisitions[acquisition.acquisition_id] = acquisition
        logger.info("Acquired modality %s with %d channels", modality, len(acquisition.channels))
        return {
            "acquisition_id": acquisition.acquisition_id,
            "modality": acquisition.modality,
            "channels": acquisition.channels,
            "sample_rate_hz": acquisition.sample_rate_hz,
            "unit": acquisition.unit,
            "typical_range": list(acquisition.typical_range),
            "impedance_unit": acquisition.impedance_unit,
            "status": acquisition.status,
            "started_at": acquisition.started_at,
        }

    def get_status(self, modality: str) -> dict[str, Any]:
        items = [v for v in self._acquisitions.values() if v.modality == modality]
        return {
            "modality": modality,
            "active_acquisitions": len(items),
            "acquisitions": [
                {
                    "acquisition_id": a.acquisition_id,
                    "channels": a.channels,
                    "sample_rate_hz": a.sample_rate_hz,
                    "status": a.status,
                    "unit": a.unit,
                }
                for a in items
            ],
        }

    def list_all(self) -> list[dict[str, Any]]:
        return [
            {
                "acquisition_id": a.acquisition_id,
                "modality": a.modality,
                "channels": a.channels,
                "sample_rate_hz": a.sample_rate_hz,
                "status": a.status,
            }
            for a in self._acquisitions.values()
        ]

    def stop(self, acquisition_id: str) -> dict[str, Any]:
        acquisition = self._acquisitions.get(acquisition_id)
        if not acquisition:
            return {"acquisition_id": acquisition_id, "status": "not_found"}
        acquisition.status = "stopped"
        return {"acquisition_id": acquisition_id, "status": "stopped"}
