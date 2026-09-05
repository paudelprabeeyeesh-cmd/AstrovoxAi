"""Integration tests for the end-to-end pipeline and production modules."""

import asyncio
import pytest
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "02-Backend"))

from app.integration.pipeline import E2EPipeline, PipelineRequest, get_e2e_pipeline
from app.integration.e2e import IntegrationTestSuite
from app.production.config import ProductionConfig, get_config, reload_config
from app.production.backup import BackupManager, get_backup_manager
from app.production.monitoring import StabilityMonitor, get_stability_monitor


class TestE2EPipeline:
    """Test the end-to-end pipeline."""
    
    def test_pipeline_creation(self):
        """Test pipeline can be created."""
        pipeline = get_e2e_pipeline()
        assert pipeline is not None
        assert pipeline.kernel is not None
    
    @pytest.mark.asyncio
    async def test_pipeline_execution(self):
        """Test pipeline execution."""
        pipeline = get_e2e_pipeline()
        request = PipelineRequest(goal="Test goal")
        response = await pipeline.execute(request)
        assert response is not None
        assert response.request_id is not None
        assert len(response.stages) > 0
        assert response.elapsed_ms >= 0
    
    @pytest.mark.asyncio
    async def test_pipeline_stages(self):
        """Test that all pipeline stages execute."""
        pipeline = get_e2e_pipeline()
        request = PipelineRequest(goal="Test stages")
        response = await pipeline.execute(request)
        
        stage_names = [stage["stage"] for stage in response.stages]
        expected_stages = [
            "api_gateway", "kernel", "planner", "compiler",
            "optimizer", "scheduler", "runtime", "worker_cluster",
            "memory_event_bus"
        ]
        
        for expected in expected_stages:
            assert expected in stage_names, f"Stage {expected} not found in {stage_names}"


class TestIntegrationSuite:
    """Test the integration test suite."""
    
    @pytest.mark.asyncio
    async def test_integration_suite(self):
        """Test the integration test suite."""
        suite = IntegrationTestSuite()
        results = await suite.run_all()
        
        assert len(results) > 0
        summary = suite.get_summary()
        assert summary["total"] == len(results)


class TestProductionConfig:
    """Test production configuration."""
    
    def test_config_from_env(self):
        """Test config creation from environment."""
        config = ProductionConfig.from_env()
        assert config is not None
        assert config.port > 0
        assert config.workers > 0
    
    def test_config_to_dict(self):
        """Test config serialization."""
        config = ProductionConfig()
        data = config.to_dict()
        assert isinstance(data, dict)
        assert "host" in data
        assert "port" in data
    
    def test_global_config(self):
        """Test global config instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2  # Should be singleton


class TestBackupManager:
    """Test backup and restore."""
    
    def test_backup_creation(self):
        """Test creating a backup."""
        manager = get_backup_manager()
        state = {"test": "data", "value": 42}
        metadata = manager.create_backup(state, ["kernel", "memory"])
        
        assert metadata.backup_id is not None
        assert "kernel" in metadata.components
        assert "memory" in metadata.components
    
    def test_backup_restore(self):
        """Test restoring from backup."""
        manager = get_backup_manager()
        state = {"test": "restore", "value": 100}
        metadata = manager.create_backup(state, ["kernel"])
        
        restored = manager.restore_backup(metadata.backup_id)
        assert restored is not None
        assert restored["test"] == "restore"
        assert restored["value"] == 100
    
    def test_list_backups(self):
        """Test listing backups."""
        manager = get_backup_manager()
        backups = manager.list_backups()
        assert isinstance(backups, list)


class TestStabilityMonitor:
    """Test stability monitoring."""
    
    def test_monitor_creation(self):
        """Test monitor can be created."""
        monitor = get_stability_monitor()
        assert monitor is not None
    
    def test_monitor_summary(self):
        """Test getting monitor summary."""
        monitor = get_stability_monitor()
        summary = monitor.get_summary()
        assert "samples" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])