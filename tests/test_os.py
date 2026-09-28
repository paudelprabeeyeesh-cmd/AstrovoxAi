import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.os.kernel import DatasetManager, GPUManager, MemoryManager, ModelManager, ModelMetadata, DatasetMetadata
from models.llm.os.runtime import ProcessManager, ResourceAllocator, Scheduler
from models.llm.os.security import APIGateway, Authentication, Authorization, Permission
from models.llm.os.package import ModelRegistry, DatasetRegistry, PluginSystem, PackageMetadata, PackageType


class TestModelManager:
    def test_register_and_list(self):
        manager = ModelManager()
        metadata = ModelMetadata(name="tiny", version="0.1", architecture="gpt2", parameters=100_000)
        manager.register(metadata)
        assert len(manager.list_models()) == 1

    def test_get_metadata(self):
        manager = ModelManager()
        metadata = ModelMetadata(name="tiny", version="0.1", architecture="gpt2", parameters=100_000)
        manager.register(metadata)
        assert manager.get_metadata("tiny").architecture == "gpt2"

    def test_load_returns_none_when_no_file(self):
        manager = ModelManager()
        metadata = ModelMetadata(name="tiny", version="0.1", architecture="gpt2", parameters=100_000)
        manager.register(metadata)
        assert manager.load("tiny", "/nonexistent/path") is None

    def test_unload_clears_cache(self):
        manager = ModelManager()
        metadata = ModelMetadata(name="tiny", version="0.1", architecture="gpt2", parameters=100_000)
        manager.register(metadata)
        manager.load("tiny", "/tmp")
        manager.unload("tiny")
        assert "tiny" not in manager._loaded

    def test_missing_model_raises(self):
        manager = ModelManager()
        try:
            manager.load("missing", "/tmp")
        except KeyError:
            pass
        else:
            raise AssertionError("Expected KeyError")


class TestDatasetManager:
    def test_register_and_list(self):
        manager = DatasetManager()
        metadata = DatasetMetadata(name="corpus", version="1.0", format="jsonl", size_bytes=1024)
        manager.register(metadata)
        assert len(manager.list_datasets()) == 1

    def test_get_path(self):
        manager = DatasetManager(cache_dir="/tmp/ds_cache")
        metadata = DatasetMetadata(name="corpus", version="1.0", format="jsonl", size_bytes=1024)
        manager.register(metadata)
        assert manager.get_path("corpus") == os.path.join("/tmp/ds_cache", "corpus")

    def test_checksum(self):
        manager = DatasetManager()
        path = "/tmp/test_checksum.txt"
        with open(path, "w") as f:
            f.write("hello")
        checksum = manager.compute_checksum(path)
        assert len(checksum) == 64
        os.remove(path)


class TestGPUManager:
    def test_detect_devices(self):
        gpu = GPUManager()
        devices = gpu.detect_devices()
        assert len(devices) >= 1

    def test_allocate_and_release(self):
        gpu = GPUManager()
        devices = gpu.detect_devices()
        if devices and devices[0]["memory_total_mb"] > 0:
            assert gpu.allocate("task-a", 128) is True
            assert gpu.allocate("task-b", 9999) is False
            gpu.release("task-a")
        else:
            assert gpu.allocate("task-a", 128) is False

    def test_status(self):
        gpu = GPUManager()
        gpu.detect_devices()
        status = gpu.status()
        assert "total_mb" in status
        assert "available_mb" in status


class TestMemoryManager:
    def test_allocate_and_snapshot(self):
        mem = MemoryManager(total_bytes=1024)
        assert mem.allocate("a", 128) is True
        snapshot = mem.snapshot()
        assert snapshot["used_bytes"] == 128

    def test_overallocate_fails(self):
        mem = MemoryManager(total_bytes=100)
        assert mem.allocate("a", 200) is False

    def test_release(self):
        mem = MemoryManager(total_bytes=1024)
        mem.allocate("a", 256)
        mem.release("a")
        assert mem.snapshot()["used_bytes"] == 0

    def test_offload(self):
        mem = MemoryManager(total_bytes=1024)
        mem.allocate("a", 128)
        target = "/tmp/offload_test.txt"
        mem.offload("a", target)
        assert os.path.exists(target)
        assert "a" not in mem._blocks
        os.remove(target)


class TestProcessManager:
    def test_spawn_completes(self):
        pm = ProcessManager()
        proc = pm.spawn("add", lambda x, y: x + y, args=(1, 2))
        assert proc.state.value == "completed"
        assert proc.result == 3

    def test_spawn_failure(self):
        pm = ProcessManager()
        proc = pm.spawn("fail", lambda: (_ for _ in ()).throw(ValueError("boom")))
        assert proc.state.value == "failed"
        assert "boom" in proc.error

    def test_terminate(self):
        pm = ProcessManager()
        proc = pm.spawn("task", lambda: None)
        pm.terminate(proc.pid)
        assert proc.state.value == "failed"

    def test_list_processes(self):
        pm = ProcessManager()
        pm.spawn("a", lambda: 1)
        pm.spawn("b", lambda: 2)
        assert len(pm.list_processes()) == 2


class TestResourceAllocator:
    def test_request_and_release(self):
        ra = ResourceAllocator()
        ra.set_capacity("gpu", 100.0)
        assert ra.request("task", "gpu", 40.0) is True
        assert ra.request("task", "gpu", 70.0) is False
        ra.release("task", "gpu")
        assert ra.usage()["gpu"]["free"] == 100.0

    def test_usage_report(self):
        ra = ResourceAllocator()
        ra.set_capacity("mem", 512.0)
        ra.request("task", "mem", 128.0)
        usage = ra.usage()
        assert usage["mem"]["used"] == 128.0


class TestScheduler:
    def test_submit_and_run(self):
        scheduler = Scheduler()
        scheduler.submit(1, lambda: 42)
        task_id, result = scheduler.run_next()
        assert task_id == 1
        assert result == 42

    def test_empty_queue(self):
        scheduler = Scheduler()
        assert scheduler.run_next() is None
        assert scheduler.pending_count() == 0

    def test_result_retrieval(self):
        scheduler = Scheduler()
        scheduler.submit(1, lambda: "ok")
        scheduler.run_next()
        assert scheduler.get_result(1) == "ok"


class TestAuthentication:
    def test_register_and_verify(self):
        auth = Authentication()
        cred = auth.register_api_key("user1", scopes=["read"])
        assert auth.verify(cred.id, cred.secret) is True

    def test_wrong_secret_rejected(self):
        auth = Authentication()
        cred = auth.register_api_key("user1")
        assert auth.verify(cred.id, "bad") is False

    def test_revoked_credential(self):
        auth = Authentication()
        cred = auth.register_api_key("user1")
        auth.revoke(cred.id)
        assert auth.verify(cred.id, cred.secret) is False


class TestAuthorization:
    def test_grant_and_check(self):
        authz = Authorization()
        authz.grant("user1", Permission(resource="model", action="read"))
        assert authz.check("user1", "model", "read") is True
        assert authz.check("user1", "model", "write") is False

    def test_role_based_access(self):
        authz = Authorization()
        authz.assign_role("user1", "admin")
        authz.grant("admin", Permission(resource="dataset", action="write"))
        assert authz.check("user1", "dataset", "write") is True


class TestAPIGateway:
    def test_route_not_found(self):
        auth = Authentication()
        authz = Authorization()
        gateway = APIGateway(auth, authz)
        response = gateway.handle_request("GET", "/missing")
        assert response["status"] == 404

    def test_authenticated_route(self):
        auth = Authentication()
        authz = Authorization()
        gateway = APIGateway(auth, authz)
        gateway.register_route("/hello", "GET", lambda name="world": {"message": f"hi {name}"}, required_scopes=["read"])
        cred = auth.register_api_key("user1", scopes=["read"])
        response = gateway.handle_request("GET", "/hello", credential_id=cred.id, secret=cred.secret)
        assert "message" in response

    def test_rate_limiting(self):
        auth = Authentication()
        authz = Authorization()
        gateway = APIGateway(auth, authz)
        gateway.set_rate_limit(max_requests=1, window_seconds=60)
        gateway.register_route("/limited", "GET", lambda: {"ok": True}, required_scopes=[])
        assert gateway.handle_request("GET", "/limited").get("ok") is True
        assert gateway.handle_request("GET", "/limited").get("status") == 429


class TestModelRegistry:
    def test_register_and_get(self):
        registry = ModelRegistry()
        metadata = PackageMetadata(name="tiny", version="0.1", package_type=PackageType.MODEL)
        registry.register(metadata)
        assert registry.get("tiny").version == "0.1"

    def test_resolve_dependencies(self):
        registry = ModelRegistry()
        registry.register(PackageMetadata(name="base", version="1.0", package_type=PackageType.MODEL, dependencies=["utils"]))
        registry.register(PackageMetadata(name="utils", version="0.5", package_type=PackageType.MODEL))
        resolved = registry.resolve_dependencies("base")
        assert "base" in resolved
        assert "utils" in resolved


class TestDatasetRegistry:
    def test_register_and_list(self):
        registry = DatasetRegistry()
        registry.register(PackageMetadata(name="corpus", version="2.0", package_type=PackageType.DATASET))
        names = [d.name for d in registry.list_datasets()]
        assert "corpus" in names


class TestPluginSystem:
    def test_install_and_call(self):
        system = PluginSystem()
        metadata = PackageMetadata(name="echo", version="0.1", package_type=PackageType.PLUGIN, entrypoint=__file__)
        plugin = system.install(metadata)
        assert plugin.name == "echo"

    def test_uninstall(self):
        system = PluginSystem()
        metadata = PackageMetadata(name="plugin", version="0.1", package_type=PackageType.PLUGIN)
        system.install(metadata)
        system.uninstall("plugin")
        assert "plugin" not in [p.name for p in system.list_plugins()]
