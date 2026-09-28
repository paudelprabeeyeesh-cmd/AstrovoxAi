import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.compiler.graph import (
    Edge,
    Node,
    Subgraph,
    ComputationGraph,
    topo_sort,
)
from models.llm.compiler.optimizer import (
    CompilerPass,
    ConstantFolder,
    DeadCodeEliminator,
    FusionPass,
    MemoryOptimizer,
)
from models.llm.compiler.kernels import (
    AutoTuner,
    KernelRegistry,
    KernelSpec,
    PerformanceModel,
)
from models.llm.compiler.codegen import (
    CPUBackend,
    CUDABackend,
    KernelCodeGenerator,
    TritonBackend,
)
from models.llm.compiler.benchmark import (
    BenchmarkComparison,
    BenchmarkRunner,
    BenchmarkResult,
    OptimizationTracker,
)


class TestComputationGraph:
    def test_add_node_and_edge(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="input"))
        g.add_node(Node(id="b", op="relu"))
        g.add_edge(Edge(source="a", target="b"))
        assert len(g.nodes) == 2
        assert len(g.edges) == 1

    def test_topological_order(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="input"))
        g.add_node(Node(id="b", op="relu"))
        g.add_node(Node(id="c", op="add"))
        g.add_edge(Edge(source="a", target="c"))
        g.add_edge(Edge(source="b", target="c"))
        g.set_outputs(["c"])
        order = topo_sort(g)
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("c")

    def test_subgraph_extraction(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="input"))
        g.add_node(Node(id="b", op="relu"))
        g.add_edge(Edge(source="a", target="b"))
        sub = g.subgraph(["a", "b"])
        assert len(sub.nodes) == 2
        assert len(sub.edges) == 1

    def test_missing_node_edge_raises(self):
        g = ComputationGraph()
        with pytest.raises(KeyError):
            g.add_edge(Edge(source="x", target="y"))


class TestOptimizer:
    def test_fusion_preserves_graph(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="input"))
        g.add_node(Node(id="b", op="relu"))
        g.add_edge(Edge(source="a", target="b"))
        g.set_outputs(["b"])
        opt = FusionPass().run(g)
        assert len(opt.nodes) == 2

    def test_dead_code_elimination(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="input"))
        g.add_node(Node(id="b", op="relu"))
        g.add_node(Node(id="c", op="const"))
        g.add_node(Node(id="d", op="add"))
        g.add_edge(Edge(source="a", target="b"))
        g.add_edge(Edge(source="c", target="d"))
        g.add_edge(Edge(source="b", target="d"))
        g.set_outputs(["b"])
        opt = DeadCodeEliminator().run(g)
        assert "c" not in opt.nodes
        assert "d" not in opt.nodes

    def test_constant_folding(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="const", attrs={"value": 1}))
        g.set_outputs(["a"])
        opt = ConstantFolder().run(g)
        assert opt.nodes["a"].op == "const_folded"

    def test_memory_optimizer_runs(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="input"))
        g.set_outputs(["a"])
        opt = MemoryOptimizer().run(g)
        assert len(opt.nodes) == 1


class TestKernelRegistry:
    def test_register_and_query(self):
        reg = KernelRegistry()
        reg.register(KernelSpec(name="add", backend="cpu", ops=["add"]))
        reg.register(KernelSpec(name="add_cuda", backend="cuda", ops=["add"]))
        assert len(reg.query("add")) == 2
        assert len(reg.query("add", backend="cuda")) == 1

    def test_autotuner_select(self):
        reg = KernelRegistry()
        reg.register(KernelSpec(name="slow", backend="cpu", ops=["add"]))
        reg.register(KernelSpec(name="fast", backend="cuda", ops=["add"]))
        tuner = AutoTuner(reg, PerformanceModel())
        choice = tuner.select("add", batch_size=1, seq_len=1, hidden_dim=1)
        assert choice.backend == "cuda"

    def test_performance_prediction(self):
        model = PerformanceModel()
        k = KernelSpec(name="k", backend="cuda", ops=["add"], tile_size=32)
        cost = model.predict(k, 1, 1, 1)
        assert cost > 0.0


class TestCodegen:
    def test_cuda_backend_generates_stub(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="input"))
        g.set_outputs(["a"])
        out = CUDABackend().generate(g, "kernel")
        assert "CUDA stub" in out
        assert "kernel" in out

    def test_triton_backend_generates_stub(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="input"))
        g.set_outputs(["a"])
        out = TritonBackend().generate(g, "triton_kernel")
        assert "Triton stub" in out

    def test_cpu_backend_generates_function(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="input"))
        g.set_outputs(["a"])
        out = CPUBackend().generate(g, "cpu_kernel")
        assert "def cpu_kernel" in out


class TestBenchmark:
    def test_benchmark_runner_returns_result(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="input"))
        g.set_outputs(["a"])
        runner = BenchmarkRunner(warmup_runs=1, runs=1)
        result = runner.run(g, "cpu")
        assert isinstance(result, BenchmarkResult)
        assert result.backend == "cpu"

    def test_optimization_tracker_speedup(self):
        tracker = OptimizationTracker()
        base = BenchmarkResult(backend="cpu", elapsed_ms=10.0)
        opt = BenchmarkResult(backend="cpu", elapsed_ms=5.0)
        entry = tracker.record(base, opt)
        assert entry["speedup"] == 2.0

    def test_benchmark_comparison(self):
        g = ComputationGraph()
        g.add_node(Node(id="a", op="input"))
        g.set_outputs(["a"])
        runner = BenchmarkRunner(warmup_runs=1, runs=1)
        tracker = OptimizationTracker()
        comp = BenchmarkComparison(runner, tracker)
        entry = comp.compare(g, "cpu")
        assert "baseline_ms" in entry
        assert "optimized_ms" in entry
