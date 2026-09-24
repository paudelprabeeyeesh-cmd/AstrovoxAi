from __future__ import annotations

import pytest
import numpy as np

from hardware_abstraction.task_171_device_abstraction import (
    CPUDevice,
    DeviceManager,
    DeviceMemory,
    DeviceType,
    GPUDevice,
    TPUDevice,
)


@pytest.fixture()
def device_manager():
    manager = DeviceManager()
    manager.register_device(CPUDevice("cpu-0", DeviceMemory(total=1024, used=128)))
    manager.register_device(GPUDevice("gpu-0", DeviceMemory(total=2048, used=0)))
    manager.register_device(TPUDevice("tpu-0", DeviceMemory(total=4096, used=512)))
    return manager


class TestDeviceMemory:
    def test_total_and_free(self):
        memory = DeviceMemory(total=1024, used=256)
        assert memory.free == 768

    def test_allocate_success(self):
        memory = DeviceMemory(total=512, used=0)
        assert memory.allocate(256) is True
        assert memory.used == 256
        assert memory.free == 256

    def test_allocate_failure(self):
        memory = DeviceMemory(total=256, used=128)
        assert memory.allocate(256) is False
        assert memory.used == 128

    def test_allocate_zero(self):
        memory = DeviceMemory(total=256, used=0)
        assert memory.allocate(0) is False

    def test_free_block(self):
        memory = DeviceMemory(total=512, used=256)
        memory.free_block(128)
        assert memory.used == 128

    def test_free_block_not_negative(self):
        memory = DeviceMemory(total=256, used=64)
        memory.free_block(128)
        assert memory.used == 0


class TestCPUDevice:
    def test_device_type(self):
        device = CPUDevice("cpu-0", DeviceMemory(total=1024, used=0))
        assert device.device_type == DeviceType.CPU

    def test_get_info(self):
        device = CPUDevice("cpu-0", DeviceMemory(total=1024, used=128))
        info = device.get_info()
        assert info["device_id"] == "cpu-0"
        assert info["device_type"] == "cpu"
        assert info["latency_ms"] == 1.0
        assert info["used_memory"] == 128
        assert info["free_memory"] == 896

    def test_allocate_tensor(self):
        device = CPUDevice("cpu-0", DeviceMemory(total=1024, used=0))
        assert device.allocate_tensor(128) == 128

    def test_allocate_tensor_failure(self):
        device = CPUDevice("cpu-0", DeviceMemory(total=256, used=256))
        assert device.allocate_tensor(128) is None

    def test_free_tensor(self):
        device = CPUDevice("cpu-0", DeviceMemory(total=1024, used=0))
        device.allocate_tensor(128)
        device.free_tensor(128)
        assert device.memory.used == 0

    def test_transfer_to(self):
        device = CPUDevice("cpu-0", DeviceMemory(total=1024, used=0))
        data = [1.0, 2.0, 3.0]
        assert device.transfer_to(data, 128) == data


class TestGPUDevice:
    def test_device_type(self):
        device = GPUDevice("gpu-0", DeviceMemory(total=2048, used=0))
        assert device.device_type == DeviceType.GPU

    def test_get_info(self):
        device = GPUDevice("gpu-0", DeviceMemory(total=2048, used=128))
        info = device.get_info()
        assert info["device_id"] == "gpu-0"
        assert info["device_type"] == "gpu"
        assert info["latency_ms"] == 0.2

    def test_allocate_tensor(self):
        device = GPUDevice("gpu-0", DeviceMemory(total=2048, used=0))
        assert device.allocate_tensor(128) == 256

    def test_free_tensor(self):
        device = GPUDevice("gpu-0", DeviceMemory(total=2048, used=0))
        device.allocate_tensor(128)
        device.free_tensor(256)
        assert device.memory.used == 0


class TestTPUDevice:
    def test_device_type(self):
        device = TPUDevice("tpu-0", DeviceMemory(total=4096, used=0))
        assert device.device_type == DeviceType.TPU

    def test_get_info(self):
        device = TPUDevice("tpu-0", DeviceMemory(total=4096, used=128))
        info = device.get_info()
        assert info["device_id"] == "tpu-0"
        assert info["device_type"] == "tpu"
        assert info["latency_ms"] == 0.1

    def test_allocate_tensor(self):
        device = TPUDevice("tpu-0", DeviceMemory(total=4096, used=0))
        assert device.allocate_tensor(128) == 512

    def test_free_tensor(self):
        device = TPUDevice("tpu-0", DeviceMemory(total=4096, used=0))
        device.allocate_tensor(128)
        device.free_tensor(512)
        assert device.memory.used == 0


class TestDeviceManager:
    def test_register_and_get_device(self, device_manager):
        device = device_manager.get_device("gpu-0")
        assert device is not None
        assert device.device_type == DeviceType.GPU

    def test_get_device_not_found(self, device_manager):
        assert device_manager.get_device("missing-0") is None

    def test_get_devices_by_type(self, device_manager):
        cpu_devices = device_manager.get_devices_by_type(DeviceType.CPU)
        assert len(cpu_devices) == 1
        assert cpu_devices[0].device_id == "cpu-0"

    def test_best_device_for_large_tensor(self, device_manager):
        best = device_manager.best_device_for(1024)
        assert best is not None
        assert best.device_id == "tpu-0"

    def test_best_device_for_small_tensor(self, device_manager):
        best = device_manager.best_device_for(32)
        assert best is not None
        assert best.device_id == "tpu-0"

    def test_best_device_for_too_large_tensor(self, device_manager):
        best = device_manager.best_device_for(16384)
        assert best is None

    def test_summary(self, device_manager):
        summary = device_manager.summary()
        assert len(summary) == 3
        ids = [entry["device_id"] for entry in summary]
        assert "cpu-0" in ids
        assert "gpu-0" in ids
        assert "tpu-0" in ids

    def test_cross_device_numerical_consistency(self, device_manager):
        cpu_device = device_manager.get_device("cpu-0")
        gpu_device = device_manager.get_device("gpu-0")
        cpu_tensor = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        gpu_tensor = gpu_device.transfer_to(cpu_tensor.tolist(), 0)
        np.testing.assert_allclose(np.array(gpu_tensor, dtype=np.float32), cpu_tensor, rtol=1e-5)
