"""Run full profiling suite against the backend hot paths (root orchestrator)."""

import asyncio
import sys
import os

BACKEND = os.path.join(os.path.dirname(__file__), "02-Backend")
sys.path.insert(0, BACKEND)


async def main():
    from scripts.profiling.endpoint_profiler import run_hot_path_profiles
    from scripts.profiling.cpu_profiler import CPUProfiler
    from scripts.profiling.async_io_audit import AsyncIOAuditor
    from scripts.profiling.memory_profiler import profile_memory_snapshot

    print("=" * 60)
    print("ENDPOINT PROFILING")
    print("=" * 60)
    try:
        endpoint_data = await run_hot_path_profiles()
        print(endpoint_data.get("summary", "No endpoint data"))
    except Exception as exc:
        print(f"Endpoint profiling failed: {exc}")

    print("\n" + "=" * 60)
    print("ASYNC I/O AUDIT")
    print("=" * 60)
    auditor = AsyncIOAuditor()
    audit_report = auditor.audit_directory(os.path.join(BACKEND, "app"))
    print(f"Violations found: {audit_report['total_violations']}")
    for v in audit_report["violations"]:
        print(f"  {v['file']}:{v['line']} in {v['function']} -> {v['detail']}")

    print("\n" + "=" * 60)
    print("MEMORY SNAPSHOT")
    print("=" * 60)
    import tracemalloc
    tracemalloc.start()
    snapshot = profile_memory_snapshot("baseline")
    tracemalloc.stop()
    print(f"Top allocations: {snapshot['total_top_kb']} KB")
    for entry in snapshot["entries"]:
        print(f"  {entry['file']}:{entry['line']}  {entry['size_kb']} KB")

    print("\nProfiling complete.")


if __name__ == "__main__":
    asyncio.run(main())
