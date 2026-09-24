import pytest
from production_readiness.blue_green import BlueGreenDeployment, DeploymentEnvironment, BlueGreenRegistry


def test_deploy():
    deployment = BlueGreenDeployment()
    env = deployment.deploy("default", "v1.0.0", "https://api.example.com", 3)
    assert env.version == "v1.0.0"
    assert env.replicas == 3


def test_switch_traffic():
    deployment = BlueGreenDeployment()
    env = deployment.deploy("default", "v1.0.0", "https://api.example.com", 3)
    result = deployment.switch_traffic("default", "v2.0.0")
    assert result["to"] == "v2.0.0"
    assert result["from"] == "v1.0.0"


def test_status():
    deployment = BlueGreenDeployment()
    deployment.deploy("default", "v1.0.0", "https://api.example.com", 3)
    status = deployment.status()
    assert "default" in status


def test_rollback():
    deployment = BlueGreenDeployment()
    env = deployment.deploy("default", "v1.0.0", "https://api.example.com", 3)
    result = deployment.rollback("default")
    assert result["rolled_back"] is True


def test_scale():
    deployment = BlueGreenDeployment()
    env = deployment.deploy("default", "v1.0.0", "https://api.example.com", 3)
    deployment.scale("default", 5)
    status = deployment.status()
    assert status["default"]["replicas"] == 5
