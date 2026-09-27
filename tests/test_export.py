import os
import sys

import pytest
import torch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.export import (
    ExportFormat,
    ExportMetadata,
    validate_export,
    report_export_sizes,
    list_supported_formats,
)


class TestExportUtilities:
    def test_list_supported_formats(self):
        formats = list_supported_formats()
        assert isinstance(formats, list)
        assert len(formats) > 0
        assert "huggingface" in formats

    def test_validate_missing_dir(self):
        result = validate_export("/nonexistent/path")
        assert result["valid"] is False
        assert "error" in result

    def test_validate_missing_metadata(self, tmp_path):
        result = validate_export(str(tmp_path))
        assert result["valid"] is False
        assert "export_metadata.json" in result["error"]

    def test_report_export_sizes_missing(self):
        with pytest.raises(FileNotFoundError):
            report_export_sizes("/nonexistent/path")

    def test_export_metadata_dataclass(self):
        meta = ExportMetadata(
            model_name="test", format="huggingface", timestamp="2024-01-01T00:00:00Z"
        )
        assert meta.model_name == "test"
        assert meta.format == "huggingface"
