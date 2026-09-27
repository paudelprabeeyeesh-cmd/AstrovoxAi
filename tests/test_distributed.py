"""
Phase F Multi-GPU Validation Test Suite
========================================

Validates distributed training strategies on multi-GPU hardware:
- DDP (DistributedDataParallel)
- FSDP (Fully Sharded Data Parallel)
- ZeRO Stage 1/2
- Tensor Parallel
- Pipeline Parallel
- CPU Offload fallback
- Distributed checkpoint save/load
- Failure recovery
- Scaling efficiency

Hardware requirements are checked at runtime; tests are skipped when
the required hardware is unavailable.
"""

import os
import sys
import time
import tempfile
import subprocess
import string

import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Project root on sys.path
# ---------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
from models.llm.distributed_training import (
    DistributedStrategy,
    DistributedTrainer,
    wrap_model,
    init_distributed,
    destroy_distributed,
    get_num_gpus,
    get_rank,
    get_world_size,
    is_distributed,
    barrier,
)

# Optional ASTROVOX_AI distributed components
try:
    from ASTROVOX_AI.ai_core.distributed import (
        ZeROOptimizer,
        ZeroConfig,
        FaultRecoveryManager,
        FaultRecoveryConfig,
    )
    HAS_ASTROVOX = True
except Exception:
    HAS_ASTROVOX = False

# Optional tensor / pipeline parallel
try:
    from torch.distributed.tensor.parallel import parallelize_module, ColwiseParallel, RowwiseParallel
    HAS_TP = True
except ImportError:
    HAS_TP = False

try:
    from torch.distributed.pipeline.sync import Pipe
    HAS_PP = True
except ImportError:
    HAS_PP = False

try:
    from accelerate import cpu_offload as _accelerate_cpu_offload
    HAS_ACCELERATE = True
except ImportError:
    HAS_ACCELERATE = False


# ---------------------------------------------------------------------------
# Hardware helpers
# ---------------------------------------------------------------------------

def has_cuda() -> bool:
    return torch.cuda.is_available()


def gpu_count() -> int:
    return torch.cuda.device_count() if has_cuda() else 0


def has_multiple_gpus() -> bool:
    return gpu_count() >= 2


def require_gpu():
    if not has_cuda():
        pytest.skip("Requires CUDA GPU")


def require_2gpus():
    if not has_multiple_gpus():
        pytest.skip("Requires 2+ CUDA GPUs")


# ---------------------------------------------------------------------------
# Tiny model / dataset for smoke tests
# ---------------------------------------------------------------------------

class TinyModel(nn.Module):
    def __init__(self, vocab_size: int = 100, hidden_size: int = 32, num_layers: int = 2):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, hidden_size)
        self.layers = nn.ModuleList(
            [nn.Linear(hidden_size, hidden_size) for _ in range(num_layers)]
        )
        self.norm = nn.LayerNorm(hidden_size)
        self.head = nn.Linear(hidden_size, vocab_size)

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        x = self.embed(input_ids)
        for layer in self.layers:
            x = F.relu(layer(x))
        x = self.norm(x)
        return self.head(x)


class TinyDataset(torch.utils.data.Dataset):
    def __init__(
        self,
        length: int = 16,
        seq_len: int = 16,
        vocab_size: int = 100,
    ):
        self.length = length
        self.seq_len = seq_len
        self.vocab_size = vocab_size

    def __len__(self) -> int:
        return self.length

    def __getitem__(self, idx: int) -> dict:
        input_ids = torch.randint(0, self.vocab_size, (self.seq_len,))
        labels = input_ids.clone()
        return {"input_ids": input_ids, "labels": labels}


# ---------------------------------------------------------------------------
# Distributed subprocess runner
# ---------------------------------------------------------------------------

_DISTRIBUTED_TEST_SCRIPT = string.Template("""\
import os
import sys

ROOT = r"$ROOT"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

$EXTRA_IMPORTS

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.distributed as dist
from torch.utils.data import DataLoader, Dataset

from models.llm.distributed_training import init_distributed, destroy_distributed, barrier


class TinyModel(nn.Module):
    def __init__(self, vocab_size=100, hidden_size=32, num_layers=2):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, hidden_size)
        self.layers = nn.ModuleList(
            [nn.Linear(hidden_size, hidden_size) for _ in range(num_layers)]
        )
        self.norm = nn.LayerNorm(hidden_size)
        self.head = nn.Linear(hidden_size, vocab_size)

    def forward(self, input_ids):
        x = self.embed(input_ids)
        for layer in self.layers:
            x = F.relu(layer(x))
        x = self.norm(x)
        return self.head(x)


class TinyDataset(Dataset):
    def __init__(self, length=16, seq_len=16, vocab_size=100):
        self.length = length
        self.seq_len = seq_len
        self.vocab_size = vocab_size

    def __len__(self):
        return self.length

    def __getitem__(self, idx):
        input_ids = torch.randint(0, self.vocab_size, (self.seq_len,))
        labels = input_ids.clone()
        return {"input_ids": input_ids, "labels": labels}


def _worker(rank, world_size, fn, args):
    os.environ["RANK"] = str(rank)
    os.environ["LOCAL_RANK"] = str(rank)
    os.environ["WORLD_SIZE"] = str(world_size)
    init_distributed(backend="nccl", init_method="env://")
    try:
        fn(rank, world_size, *args)
    finally:
        destroy_distributed()


$TEST_LOGIC

if __name__ == "__main__":
    import torch.multiprocessing as mp
    mp.spawn(_worker, args=(test_fn, ()), nprocs=2, join=True)
""")


def _run_distributed_2gpus(test_logic: str, extra_imports: str = "", env: dict | None = None):
    """Run *test_logic* in a 2-GPU subprocess.

    The generated script is executed as ``__main__`` so that
    ``torch.multiprocessing.spawn`` can re-import it cleanly on Windows.
    """
    require_2gpus()

    script = _DISTRIBUTED_TEST_SCRIPT.substitute(
        ROOT=ROOT.replace("\\", "\\\\"),
        EXTRA_IMPORTS=extra_imports,
        TEST_LOGIC=test_logic.replace("$", "$$"),
    )

    fd, script_path = tempfile.mkstemp(suffix=".py")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(script)

        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        result = subprocess.run(
            [sys.executable, script_path],
            env=run_env,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            pytest.fail(
                "Distributed subprocess failed:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
    finally:
        if os.path.exists(script_path):
            os.unlink(script_path)


# ===========================================================================
# Test classes
# ===========================================================================


class TestDistributedSetup:
    """Environment and helper smoke tests (no GPU required)."""

    def test_cuda_available(self):
        if not has_cuda():
            pytest.skip("CUDA not available")
        assert torch.cuda.is_available()

    def test_gpu_count_reported(self):
        count = gpu_count()
        assert count >= 0
        assert count == torch.cuda.device_count()

    def test_environment_helpers(self):
        assert get_num_gpus() == gpu_count()
        assert get_rank() == int(os.environ.get("RANK", os.environ.get("LOCAL_RANK", "0")))
        assert get_world_size() == int(os.environ.get("WORLD_SIZE", "1"))
        assert is_distributed() == (get_world_size() > 1)

    def test_barrier_noop_undistributed(self):
        barrier()

    def test_log_memory_no_cuda(self):
        if has_cuda():
            pytest.skip("Requires CPU-only environment")
        from models.llm.distributed_training import log_memory_usage
        log_memory_usage("test")


class TestDDP:
    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_ddp_2gpu_forward(self):
        _run_distributed_2gpus("""
def test_fn(rank, world_size):
    model = TinyModel().to(f"cuda:{rank}")
    ddp = nn.parallel.DistributedDataParallel(model, device_ids=[rank])
    x = torch.randint(0, 100, (4, 16), device=f"cuda:{rank}")
    out = ddp(x)
    assert out.shape == (4, 16, 100)
""")

    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_ddp_gradient_sync(self):
        _run_distributed_2gpus("""
def test_fn(rank, world_size):
    torch.manual_seed(42 + rank)
    model = TinyModel().to(f"cuda:{rank}")
    ddp = nn.parallel.DistributedDataParallel(model, device_ids=[rank])
    x = torch.randint(0, 100, (4, 16), device=f"cuda:{rank}")
    out = ddp(x)
    loss = out.sum()
    loss.backward()
    for p in ddp.parameters():
        if p.grad is not None:
            assert not torch.isnan(p.grad).any()
            assert not torch.isinf(p.grad).any()
""")

    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_ddp_train_step(self):
        _run_distributed_2gpus("""
def test_fn(rank, world_size):
    model = TinyModel().to(f"cuda:{rank}")
    ddp = nn.parallel.DistributedDataParallel(model, device_ids=[rank])
    optimizer = torch.optim.SGD(ddp.parameters(), lr=0.01)
    dataset = TinyDataset()
    loader = DataLoader(dataset, batch_size=2)
    ddp.train()
    total_loss = 0.0
    for batch in loader:
        input_ids = batch["input_ids"].to(f"cuda:{rank}")
        labels = batch["labels"].to(f"cuda:{rank}")
        optimizer.zero_grad()
        out = ddp(input_ids)
        loss = F.cross_entropy(out.view(-1, 100), labels.view(-1))
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    assert total_loss > 0
""")


class TestFSDP:
    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_fsdp_2gpu_forward(self):
        _run_distributed_2gpus("""
def test_fn(rank, world_size):
    from torch.distributed.fsdp import (
        FullyShardedDataParallel as FSDP,
        MixedPrecision,
        BackwardPrefetch,
        ShardingStrategy,
    )
    model = TinyModel().to(f"cuda:{rank}")
    fsdp = FSDP(
        model,
        mixed_precision=MixedPrecision(
            param_dtype=torch.float16,
            reduce_dtype=torch.float16,
            buffer_dtype=torch.float32,
        ),
        sharding_strategy=ShardingStrategy.FULL_SHARD,
        backward_prefetch=BackwardPrefetch.BACKWARD_PRE,
    )
    x = torch.randint(0, 100, (4, 16), device=f"cuda:{rank}")
    out = fsdp(x)
    assert out.shape == (4, 16, 100)
""")

    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_fsdp_gradient_sync(self):
        _run_distributed_2gpus("""
def test_fn(rank, world_size):
    from torch.distributed.fsdp import (
        FullyShardedDataParallel as FSDP,
        MixedPrecision,
        BackwardPrefetch,
        ShardingStrategy,
    )
    torch.manual_seed(42 + rank)
    model = TinyModel().to(f"cuda:{rank}")
    fsdp = FSDP(
        model,
        mixed_precision=MixedPrecision(
            param_dtype=torch.float16,
            reduce_dtype=torch.float16,
            buffer_dtype=torch.float32,
        ),
        sharding_strategy=ShardingStrategy.FULL_SHARD,
        backward_prefetch=BackwardPrefetch.BACKWARD_PRE,
    )
    x = torch.randint(0, 100, (4, 16), device=f"cuda:{rank}")
    out = fsdp(x)
    loss = out.sum()
    loss.backward()
    for p in fsdp.parameters():
        if p.grad is not None:
            assert not torch.isnan(p.grad).any()
            assert not torch.isinf(p.grad).any()
""")

    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_fsdp_train_step(self):
        _run_distributed_2gpus("""
def test_fn(rank, world_size):
    from torch.distributed.fsdp import (
        FullyShardedDataParallel as FSDP,
        MixedPrecision,
        BackwardPrefetch,
        ShardingStrategy,
    )
    model = TinyModel().to(f"cuda:{rank}")
    fsdp = FSDP(
        model,
        mixed_precision=MixedPrecision(
            param_dtype=torch.float16,
            reduce_dtype=torch.float16,
            buffer_dtype=torch.float32,
        ),
        sharding_strategy=ShardingStrategy.FULL_SHARD,
        backward_prefetch=BackwardPrefetch.BACKWARD_PRE,
    )
    optimizer = torch.optim.SGD(fsdp.parameters(), lr=0.01)
    dataset = TinyDataset()
    loader = DataLoader(dataset, batch_size=2)
    fsdp.train()
    total_loss = 0.0
    for batch in loader:
        input_ids = batch["input_ids"].to(f"cuda:{rank}")
        labels = batch["labels"].to(f"cuda:{rank}")
        optimizer.zero_grad()
        out = fsdp(input_ids)
        loss = F.cross_entropy(out.view(-1, 100), labels.view(-1))
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    assert total_loss > 0
""")


class TestZeRO:
    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_zero_stage1_2gpu(self):
        require_2gpus()
        if not HAS_ASTROVOX:
            pytest.skip("ASTROVOX_AI ZeRO optimizer not available")
        _run_distributed_2gpus(
            """
def test_fn(rank, world_size):
    from ASTROVOX_AI.ai_core.distributed import ZeROOptimizer, ZeroConfig
    model = TinyModel().to(f"cuda:{rank}")
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    zero_cfg = ZeroConfig(stage=1, world_size=world_size, rank=rank)
    zero_opt = ZeROOptimizer(model, optimizer, zero_cfg)
    x = torch.randint(0, 100, (4, 16), device=f"cuda:{rank}")
    out = model(x)
    loss = out.sum()
    zero_opt.backward(loss)
    zero_opt.step()
    zero_opt.zero_grad()
""",
            extra_imports="from ASTROVOX_AI.ai_core.distributed import ZeROOptimizer, ZeroConfig",
        )

    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_zero_stage2_2gpu(self):
        require_2gpus()
        if not HAS_ASTROVOX:
            pytest.skip("ASTROVOX_AI ZeRO optimizer not available")
        _run_distributed_2gpus(
            """
def test_fn(rank, world_size):
    from ASTROVOX_AI.ai_core.distributed import ZeROOptimizer, ZeroConfig
    model = TinyModel().to(f"cuda:{rank}")
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    zero_cfg = ZeroConfig(stage=2, world_size=world_size, rank=rank)
    zero_opt = ZeROOptimizer(model, optimizer, zero_cfg)
    x = torch.randint(0, 100, (4, 16), device=f"cuda:{rank}")
    out = model(x)
    loss = out.sum()
    zero_opt.backward(loss)
    zero_opt.step()
    zero_opt.zero_grad()
""",
            extra_imports="from ASTROVOX_AI.ai_core.distributed import ZeROOptimizer, ZeroConfig",
        )


class TestTensorParallel:
    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_tensor_parallel_available(self):
        if not HAS_TP:
            pytest.skip("torch.distributed.tensor not available")

    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_tensor_parallel_2gpu(self):
        require_2gpus()
        if not HAS_TP:
            pytest.skip("torch.distributed.tensor not available")
        _run_distributed_2gpus("""
def test_fn(rank, world_size):
    model = TinyModel().to(f"cuda:{rank}")
    tp_mesh = torch.distributed.device_mesh.init_device_mesh("cuda", (world_size,))
    parallelize_module(model, tp_mesh, {"": ColwiseParallel(), "": RowwiseParallel()})
    x = torch.randint(0, 100, (4, 16), device=f"cuda:{rank}")
    out = model(x)
    assert out.shape == (4, 16, 100)
""")


class TestPipelineParallel:
    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_pipeline_parallel_available(self):
        if not HAS_PP:
            pytest.skip("torch.distributed.pipeline not available")

    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_pipeline_parallel_2gpu(self):
        require_2gpus()
        if not HAS_PP:
            pytest.skip("torch.distributed.pipeline not available")
        _run_distributed_2gpus("""
def test_fn(rank, world_size):
    model = TinyModel().to(f"cuda:{rank}")
    pipe = Pipe(model, chunks=2)
    x = torch.randint(0, 100, (4, 16), device=f"cuda:{rank}")
    out = pipe(x)
    assert out.shape == (4, 16, 100)
""")


class TestCPUOffload:
    def test_cpu_offload_fallback_cpu(self):
        model = TinyModel()
        device = torch.device("cpu")
        wrapped = wrap_model(model, DistributedStrategy.CPU_OFFLOAD, device=device)
        assert wrapped is not None
        x = torch.randint(0, 100, (2, 8))
        out = wrapped(x)
        assert out.shape == (2, 8, 100)

    @pytest.mark.gpu
    def test_cpu_offload_cuda(self):
        require_gpu()
        model = TinyModel().to("cuda")
        wrapped = wrap_model(model, DistributedStrategy.CPU_OFFLOAD, device=torch.device("cuda"))
        assert wrapped is not None
        x = torch.randint(0, 100, (2, 8), device="cuda")
        out = wrapped(x)
        assert out.shape == (2, 8, 100)

    def test_cpu_offload_without_accelerate(self):
        model = TinyModel()
        device = torch.device("cpu")
        wrapped = wrap_model(model, DistributedStrategy.CPU_OFFLOAD, device=device)
        assert wrapped is not None


class TestCheckpointDistributed:
    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_save_load_distributed_checkpoint(self):
        require_2gpus()
        ckpt_dir = tempfile.mkdtemp()
        try:
            _run_distributed_2gpus(
                """
def test_fn(rank, world_size):
    from models.llm.distributed_training import DistributedTrainer, DistributedStrategy
    ckpt_dir = os.environ.get("TEST_CKPT_DIR", ".")
    model = TinyModel().to(f"cuda:{rank}")
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lambda step: 1.0)
    trainer = DistributedTrainer(
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        strategy=DistributedStrategy.DDP,
        device=torch.device(f"cuda:{rank}"),
        checkpoint_dir=ckpt_dir,
        use_amp=False,
    )
    x = torch.randint(0, 100, (4, 16), device=f"cuda:{rank}")
    out = trainer.model(x)
    loss = out.sum()
    loss.backward()
    trainer.optimizer.step()
    trainer.optimizer.zero_grad()
    if rank == 0:
        trainer.save_checkpoint("test_ckpt.pt")
    barrier()
    if rank == 0:
        trainer.load_checkpoint("test_ckpt.pt")
""",
                env={"TEST_CKPT_DIR": ckpt_dir.replace("\\", "/")},
            )
        finally:
            import shutil
            shutil.rmtree(ckpt_dir, ignore_errors=True)

    def test_save_load_single_device(self):
        ckpt_dir = tempfile.mkdtemp()
        try:
            model = TinyModel()
            optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
            scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lambda step: 1.0)

            x = torch.randint(0, 100, (4, 16))
            out = model(x)
            loss = out.sum()
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

            os.makedirs(ckpt_dir, exist_ok=True)
            state = {
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "step": 1,
            }
            ckpt_path = os.path.join(ckpt_dir, "single_ckpt_1.pt")
            torch.save(state, ckpt_path)
            loaded = torch.load(ckpt_path, map_location="cpu", weights_only=False)
            model.load_state_dict(loaded["model"])
            optimizer.load_state_dict(loaded["optimizer"])
            scheduler.load_state_dict(loaded["scheduler"])
            assert loaded["step"] == 1
        finally:
            import shutil
            shutil.rmtree(ckpt_dir, ignore_errors=True)


class TestFailureRecovery:
    def test_fault_recovery_manager_init(self):
        if not HAS_ASTROVOX:
            pytest.skip("ASTROVOX_AI FaultRecoveryManager not available")
        ckpt_dir = tempfile.mkdtemp()
        try:
            config = FaultRecoveryConfig(
                max_retries=3,
                retry_delay=0.1,
                checkpoint_dir=ckpt_dir,
            )
            manager = FaultRecoveryManager(config)
            assert manager is not None
            assert manager.config.max_retries == 3
        finally:
            import shutil
            shutil.rmtree(ckpt_dir, ignore_errors=True)

    def test_fault_recovery_state_roundtrip(self):
        if not HAS_ASTROVOX:
            pytest.skip("ASTROVOX_AI FaultRecoveryManager not available")
        ckpt_dir = tempfile.mkdtemp()
        try:
            config = FaultRecoveryConfig(
                max_retries=2,
                retry_delay=0.05,
                checkpoint_dir=ckpt_dir,
            )
            manager = FaultRecoveryManager(config)
            model = TinyModel()
            manager.save_state(model, step=5)
            loaded_step = manager.load_state(model)
            assert loaded_step == 5
        finally:
            import shutil
            shutil.rmtree(ckpt_dir, ignore_errors=True)


class TestScalingEfficiency:
    @pytest.mark.gpu
    @pytest.mark.distributed
    def test_scaling_efficiency_1_vs_2_gpus(self):
        require_2gpus()

        # Single-GPU baseline
        torch.manual_seed(42)
        model_single = TinyModel().to("cuda:0")
        optimizer_single = torch.optim.SGD(model_single.parameters(), lr=0.01)
        dataset = TinyDataset()
        loader = torch.utils.data.DataLoader(dataset, batch_size=2)

        model_single.train()
        start_single = time.perf_counter()
        total_loss_single = 0.0
        steps_single = 0
        for batch in loader:
            input_ids = batch["input_ids"].to("cuda:0")
            labels = batch["labels"].to("cuda:0")
            optimizer_single.zero_grad()
            out = model_single(input_ids)
            loss = F.cross_entropy(out.view(-1, 100), labels.view(-1))
            loss.backward()
            optimizer_single.step()
            total_loss_single += loss.item()
            steps_single += 1
        time_single = time.perf_counter() - start_single
        avg_loss_single = total_loss_single / steps_single if steps_single > 0 else 0.0

        # 2-GPU DDP via subprocess
        results_file = tempfile.mktemp(suffix=".pkl")
        try:
            _run_distributed_2gpus(
                f"""
def test_fn(rank, world_size):
    import pickle
    results_file = os.environ.get("TEST_RESULTS_FILE", "")
    model = TinyModel().to(f"cuda:{{rank}}")
    if world_size > 1:
        model = nn.parallel.DistributedDataParallel(model, device_ids=[rank])
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    dataset = TinyDataset()
    loader = DataLoader(dataset, batch_size=2)
    model.train()
    start = time.perf_counter()
    total_loss = 0.0
    steps = 0
    for batch in loader:
        input_ids = batch["input_ids"].to(f"cuda:{{rank}}")
        labels = batch["labels"].to(f"cuda:{{rank}}")
        optimizer.zero_grad()
        out = model(input_ids)
        loss = F.cross_entropy(out.view(-1, 100), labels.view(-1))
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        steps += 1
    elapsed = time.perf_counter() - start
    avg_loss = total_loss / steps if steps > 0 else 0.0
    if rank == 0 and results_file:
        with open(results_file, "wb") as f:
            pickle.dump({{"elapsed": elapsed, "avg_loss": avg_loss, "steps": steps}})
""",
                env={"TEST_RESULTS_FILE": results_file.replace("\\", "/")},
            )
            with open(results_file, "rb") as fh:
                results = pickle.load(fh)
            time_multi = results["elapsed"]
            avg_loss_multi = results["avg_loss"]

            speedup = time_single / time_multi if time_multi > 0 else 0.0
            assert speedup > 0.3, f"Scaling efficiency too low: speedup={speedup:.2f}"
            assert abs(avg_loss_single - avg_loss_multi) < 2.0
        finally:
            if os.path.exists(results_file):
                os.unlink(results_file)
