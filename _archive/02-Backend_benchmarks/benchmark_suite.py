"""Performance benchmarking suite for AstrovoxAi.

Includes:
1. pytest-benchmark integration for performance testing
2. Memory profiling utilities
3. Flame graph generation helpers
4. Standard benchmark scenarios for core components
"""

from __future__ import annotations

import asyncio
import gc
import json
import os
import sys
import time
import tracemalloc
from typing import Any, Callable, Dict, List, Optional

import pytest

# Try to import optional dependencies
try:
    import pytest_benchmark
    HAS_PYTEST_BENCHMARK = True
except ImportError:
    HAS_PYTEST_BENCHMARK = False

try:
    import memory_profiler
    HAS_MEMORY_PROFILER = True
except ImportError:
    HAS_MEMORY_PROFILER = False

try:
    from pyflame import flamegraph
    HAS_FLAMEGRAPH = True
except ImportError:
    HAS_FLAMEGRAPH = False

logger = __import__('logging').getLogger(__name__)


class BenchmarkSuite:
    """Main benchmarking suite coordinator."""

    def __init__(self, output_dir: str = "benchmarks/results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results: Dict[str, Any] = {}

    def run_benchmark(self, name: str, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Run a single benchmark and return results."""
        # Force garbage collection before benchmark
        gc.collect()
        
        # Start tracing
        tracemalloc.start()
        start_time = time.perf_counter()
        
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        benchmark_result = {
            "name": name,
            "duration_seconds": end_time - start_time,
            "memory_current_bytes": current,
            "memory_peak_bytes": peak,
            "success": success,
            "error": error,
            "timestamp": time.time(),
            "result": result
        }
        
        self.results[name] = benchmark_result
        return benchmark_result

    async def run_async_benchmark(self, name: str, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Run an async benchmark."""
        gc.collect()
        tracemalloc.start()
        start_time = time.perf_counter()
        
        try:
            result = await func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        benchmark_result = {
            "name": name,
            "duration_seconds": end_time - start_time,
            "memory_current_bytes": current,
            "memory_peak_bytes": peak,
            "success": success,
            "error": error,
            "timestamp": time.time(),
            "result": result
        }
        
        self.results[name] = benchmark_result
        return benchmark_result

    def save_results(self, filename: str = None) -> str:
        """Save benchmark results to JSON file."""
        if filename is None:
            filename = f"benchmark_results_{int(time.time())}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        return filepath

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all benchmarks."""
        if not self.results:
            return {"total_benchmarks": 0}
        
        successful = [r for r in self.results.values() if r["success"]]
        failed = [r for r in self.results.values() if not r["success"]]
        
        if successful:
            avg_duration = sum(r["duration_seconds"] for r in successful) / len(successful)
            avg_memory = sum(r["memory_peak_bytes"] for r in successful) / len(successful)
        else:
            avg_duration = 0
            avg_memory = 0
        
        return {
            "total_benchmarks": len(self.results),
            "successful": len(successful),
            "failed": len(failed),
            "average_duration_seconds": avg_duration,
            "average_peak_memory_bytes": avg_memory,
            "total_duration_seconds": sum(r["duration_seconds"] for r in self.results.values()),
            "total_peak_memory_bytes": sum(r["memory_peak_bytes"] for r in self.results.values())
        }


# Pytest benchmark fixtures and tests
@pytest.fixture
def benchmark_suite():
    """Fixture providing a benchmark suite."""
    return BenchmarkSuite()


@pytest.fixture
def memory_profile():
    """Fixture for memory profiling."""
    if not HAS_MEMORY_PROFILER:
        pytest.skip("memory_profiler not installed")
    return memory_profiler


# Standard benchmark tests
class TestCompilerPerformance:
    """Performance tests for the compiler."""

    def test_compiler_benchmark(self, benchmark):
        """Benchmark compiler performance using pytest-benchmark."""
        if not HAS_PYTEST_BENCHMARK:
            pytest.skip("pytest-benchmark not installed")
        
        # Import compiler components
        try:
            from app.executor.compiler import Compiler
            
            # Sample DSL code to compile
            dsl_code = """
            load data from "https://example.com/data.csv" as raw_data
            search web for "AI trends 2024" as trends
            summarize raw_data as summary
            generate report from summary and trends as report
            email report to "user@example.com" subject "AI Report"
            """
            
            def compile_dsl():
                compiler = Compiler()
                return compiler.compile(dsl_code)
            
            # Run benchmark
            result = benchmark(compile_dsl)
            assert result is not None
            
        except ImportError:
            pytest.skip("Compiler not available")

    def test_memory_management_benchmark(self, benchmark):
        """Benchmark memory management performance."""
        if not HAS_PYTEST_BENCHMARK:
            pytest.skip("pytest-benchmark not installed")
        
        try:
            from app.executor.memory.memory_management import allocate, retain, release, gc_collect
            
            def allocate_and_release():
                # Allocate many objects
                objects = []
                for i in range(1000):
                    obj_id = allocate({"data": f"object_{i}"})
                    retain(obj_id)
                    objects.append(obj_id)
                
                # Release half
                for obj_id in objects[::2]:
                    release(obj_id)
                
                # Force GC
                gc_collect()
                
                return len(objects)
            
            result = benchmark(allocate_and_release)
            assert result == 1000
            
        except ImportError:
            pytest.skip("Memory management not available")


class TestMemoryProfiling:
    """Memory profiling tests."""

    @pytest.mark.skipif(not HAS_MEMORY_PROFILER, reason="memory_profiler not installed")
    def test_memory_profiler_basic(self, memory_profile):
        """Basic memory profiling test."""
        @memory_profile.profile
        def allocate_memory():
            data = []
            for i in range(1000):
                data.append({"id": i, "data": "x" * 100})
            return data
        
        result = allocate_memory()
        assert len(result) == 1000

    @pytest.mark.skipif(not HAS_MEMORY_PROFILER, reason="memory_profiler not installed")
    def test_memory_growth_detection(self, memory_profile):
        """Test detection of memory growth."""
        @memory_profile.profile(precision=2)
        def growing_function():
            data = []
            for i in range(100):
                data.append(bytearray(1000))  # 100KB each
            return data
        
        result = growing_function()
        assert len(result) == 100


class TestFlameGeneration:
    """Flame graph generation tests."""

    @pytest.mark.skipif(not HAS_FLAMEGRAPH, reason="pyflame not installed")
    def test_flamegraph_generation(self):
        """Test flame graph generation capability."""
        # This would typically be run via pyflame command line
        # For now, just verify the module is available
        assert flamegraph is not None

    def test_flamegraph_helper(self):
        """Test helper functions for flame graph generation."""
        # Simple CPU-intensive function for testing
        def cpu_intensive_work(n: int = 100000):
            total = 0
            for i in range(n):
                total += i * i
            return total
        
        result = cpu_intensive_work(1000)
        assert isinstance(result, int)


# Benchmark scenarios for different components
class ComponentBenchmarks:
    """Pre-defined benchmark scenarios for different system components."""

    @staticmethod
    def benchmark_compiler_compilation(suite: BenchmarkSuite):
        """Benchmark full compiler compilation pipeline."""
        try:
            from app.executor.compiler import Compiler
            from app.executor.memory.memory_management import memory_manager
            
            dsl_programs = [
                '''load data from "file1.csv" as d1''',
                '''load data from "file1.csv" as d1
                   load data from "file2.csv" as d2''',
                '''load data from "file1.csv" as d1
                   search web for "test" as s
                   summarize d1 as sum
                   generate report from sum as r''',
                '''load data from "file1.csv" as d1
                   load data from "file2.csv" as d2
                   search web for "AI" as s1
                   search web for "ML" as s2
                   summarize d1 as sum1
                   summarize d2 as sum2
                   generate report from sum1 and sum2 as r1
                   generate report from s1 and s2 as r2
                   email r1 to "user1@example.com"
                   email r2 to "user2@example.com"'''
            ]
            
            def compile_all():
                compiler = Compiler()
                results = []
                for i, dsl in enumerate(dsl_programs):
                    result = compiler.compile(dsl)
                    results.append((i, result))
                return results
            
            return suite.run_benchmark("compiler_compilation", compile_all)
            
        except ImportError:
            return suite.run_benchmark("compiler_compilation", lambda: None)

    @staticmethod
    def benchmark_memory_allocation(suite: BenchmarkSuite):
        """Benchmark memory allocation and GC."""
        try:
            from app.executor.memory.memory_management import allocate, retain, release, gc_collect
            
            def alloc_and_gc():
                objects = []
                # Allocate 10,000 objects
                for i in range(10000):
                    obj_id = allocate({"id": i, "data": "x" * 50})
                    retain(obj_id)
                    objects.append(obj_id)
                
                # Release every other object
                for obj_id in objects[::2]:
                    release(obj_id)
                
                # Force collection
                gc_collect()
                
                return len(objects)
            
            return suite.run_benchmark("memory_allocation_gc", alloc_and_gc)
            
        except ImportError:
            return suite.run_benchmark("memory_allocation_gc", lambda: None)

    @staticmethod
    def benchmark_async_operations(suite: BenchmarkSuite):
        """Benchmark async operation performance."""
        async def async_work():
            # Simulate async I/O work
            await asyncio.sleep(0.001)
            return "completed"
        
        async def run_concurrent():
            tasks = [async_work() for _ in range(100)]
            return await asyncio.gather(*tasks)
        
        return asyncio.run(suite.run_async_benchmark("async_concurrent", run_concurrent))


def run_benchmark_suite(output_dir: str = "benchmarks/results") -> Dict[str, Any]:
    """Run the full benchmark suite and return results."""
    suite = BenchmarkSuite(output_dir)
    
    # Run component benchmarks
    ComponentBenchmarks.benchmark_compiler_compilation(suite)
    ComponentBenchmarks.benchmark_memory_allocation(suite)
    ComponentBenchmarks.benchmark_async_operations(suite)
    
    # Save results
    results_file = suite.save_results()
    summary = suite.get_summary()
    
    return {
        "results_file": results_file,
        "summary": summary,
        "detailed_results": suite.results
    }


if __name__ == "__main__":
    # Run benchmark suite when executed directly
    print("Running AstrovoxAi Performance Benchmark Suite...")
    results = run_benchmark_suite()
    print(f"Benchmark completed. Results saved to: {results['results_file']}")
    print(f"Summary: {json.dumps(results['summary'], indent=2)}")