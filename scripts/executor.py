"""Astrovox Task Executor: loops through all phases 41-80 + future roadmap,
implementing and testing each subtask. Failed tasks are skipped and logged;
the loop continues until stopped.

Usage: python scripts/executor.py [--stop] [--batch N] [--phase N]
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Make project root and scripts dir importable before importing builders.
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
if str(BASE / "scripts") not in sys.path:
    sys.path.insert(0, str(BASE / "scripts"))

BASE = Path(__file__).resolve().parent.parent
STATE_FILE = BASE / "scripts" / "state" / "progress.json"
BATCH_SIZE = int(os.environ.get("EXECUTOR_BATCH", "8"))

# Import all phase builders so the executor can dispatch to them.
import importlib
_builders = importlib.import_module("scripts.phases.builders")

# ============ PHASES (execution order) ============
PHASES = [
    (41, "Multi-Agent System", [
        "agent_framework", "planner_agent", "coding_agent", "research_agent",
        "testing_agent", "debugging_agent", "memory_agent", "tool_calling",
        "agent_communication", "task_scheduler",
    ]),
    (42, "Long-Term Memory", [
        "memory_storage", "conversation_memory", "user_profiles", "knowledge_memory",
        "memory_ranking", "memory_retrieval", "memory_compression",
        "memory_summarization", "memory_cleanup",
    ]),
    (43, "RAG Engine", [
        "document_loader", "pdf_parser", "docx_parser", "markdown_parser",
        "chunking_engine", "embedding_pipeline", "retriever", "reranker",
        "citation_engine",
    ]),
    (44, "Search Engine", [
        "local_search", "hybrid_search", "semantic_search", "keyword_search",
        "search_ranking", "search_cache",
    ]),
    (45, "Vector Database", [
        "embedding_storage", "similarity_search", "index_builder",
        "vector_compression", "metadata_storage",
    ]),
    (46, "API Platform", [
        "rest_api", "websocket_api", "sdk_python", "sdk_javascript",
        "authentication", "api_keys", "rate_limiting",
    ]),
    (47, "Dashboard", [
        "admin_dashboard", "user_dashboard", "analytics", "monitoring",
        "usage_statistics", "logs_viewer",
    ]),
    (48, "Model Management", [
        "model_registry", "model_downloader", "model_loader", "model_versioning",
        "model_cache", "model_switching",
    ]),
    (49, "Training Platform", [
        "dataset_manager", "trainer_ui", "hyperparameter_search",
        "experiment_tracking", "checkpoint_manager",
    ]),
    (50, "Inference Server", [
        "batch_inference", "streaming_responses", "request_queue", "load_balancer",
        "session_manager",
    ]),
    (51, "Plugin Marketplace", [
        "plugin_registry", "plugin_installer", "plugin_updates", "permission_system",
        "plugin_sandbox",
    ]),
    (52, "Security", [
        "user_authentication", "authorization", "encryption", "secret_manager",
        "audit_logs", "backup_system",
    ]),
    (53, "Performance", [
        "benchmark_suite", "memory_profiler", "cpu_profiler", "gpu_support",
        "kernel_optimization", "cache_optimizer",
    ]),
    (54, "Deployment", [
        "docker_images", "kubernetes_support", "auto_updates", "cloud_deployment",
        "local_installer",
    ]),
    (55, "Developer Tools", [
        "cli", "project_generator", "code_templates", "extension_api", "debug_tools",
    ]),
    (56, "AI Studio", [
        "prompt_builder", "workflow_editor", "visual_agent_builder", "pipeline_designer",
    ]),
    (57, "Enterprise", [
        "organizations", "teams", "roles", "permissions", "billing_hooks",
    ]),
    (58, "Integrations", [
        "github", "gitlab", "vscode", "discord", "slack", "notion",
    ]),
    (59, "Documentation", [
        "api_docs", "tutorials", "examples", "architecture_docs", "contribution_guide",
    ]),
    (60, "Production Release", [
        "final_testing", "stress_testing", "security_audit", "performance_audit",
        "stable_release", "long_term_support",
    ]),
    (61, "AI Reasoning", [
        "chain_of_thought", "planning_engine", "reflection_engine", "self_correction",
        "decision_trees", "goal_management", "reasoning_graph", "multi_step_planning",
    ]),
    (62, "Multimodal AI", [
        "image_understanding", "ocr_engine", "video_understanding", "audio_understanding",
        "speech_recognition", "text_to_speech", "image_generation", "video_generation",
    ]),
    (63, "Robotics Interfaces", [
        "robot_control_api", "sensor_interface", "camera_interface", "motion_planning",
        "navigation", "simulation_support",
    ]),
    (64, "Computer Vision", [
        "object_detection", "image_segmentation", "pose_estimation", "face_detection",
        "ocr_pipeline", "video_tracking",
    ]),
    (65, "Audio & Speech", [
        "speech_to_text", "text_to_speech", "speaker_recognition", "voice_cloning",
        "audio_enhancement", "noise_reduction",
    ]),
    (66, "Research Platform", [
        "paper_library", "experiment_manager", "benchmark_hub", "model_comparison",
        "reproducibility_tools", "result_visualization",
    ]),
    (67, "Distributed AI", [
        "distributed_training", "distributed_inference", "worker_nodes",
        "parameter_server", "cluster_scheduler", "fault_recovery",
    ]),
    (68, "Edge AI", [
        "mobile_runtime", "raspberry_pi", "edge_optimization", "offline_inference",
        "lightweight_models",
    ]),
    (69, "Compiler & Runtime", [
        "graph_compiler", "jit_compiler", "operator_fusion", "runtime_optimizer",
        "execution_scheduler", "memory_optimizer",
    ]),
    (70, "Hardware Acceleration", [
        "cuda_backend", "rocm_backend", "vulkan_compute", "opencl_backend",
        "simd_optimization", "cpu_kernel_library",
    ]),
    (71, "Model Compression", [
        "quantization", "pruning", "distillation", "weight_sharing", "sparse_models",
    ]),
    (72, "Autonomous Systems", [
        "workflow_automation", "multi_agent_collab", "task_orchestration",
        "autonomous_scheduling", "event_engine",
    ]),
    (73, "Ecosystem", [
        "extension_marketplace", "community_plugins", "templates", "sample_projects",
        "package_registry",
    ]),
    (74, "Observability", [
        "metrics_collection", "distributed_tracing", "error_reporting",
        "performance_dashboard", "health_monitoring",
    ]),
    (75, "Production Scale", [
        "high_availability", "horizontal_scaling", "load_testing", "failover",
        "disaster_recovery",
    ]),
    (76, "AI Governance", [
        "model_version_governance", "dataset_tracking", "experiment_lineage",
        "audit_trails", "compliance_tools",
    ]),
    (77, "SDK Ecosystem", [
        "python_sdk", "cpp_sdk", "javascript_sdk", "java_sdk", "go_sdk", "rust_sdk",
    ]),
    (78, "Education", [
        "interactive_tutorials", "playground", "learning_paths", "example_gallery",
        "demo_applications",
    ]),
    (79, "Release Engineering", [
        "automated_releases", "version_management", "release_notes", "package_publishing",
        "binary_distribution",
    ]),
    (80, "Astrovox 1.0", [
        "feature_freeze", "full_documentation", "api_review", "performance_validation",
        "security_review", "stability_testing", "public_release", "lts_commitment",
    ]),
]


# ============ STATE MANAGEMENT ============
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"done": [], "skipped": [], "started": [], "runs": 0, "last_run": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_done(phase: int, task: str) -> bool:
    return f"{phase}:{task}" in set(state["done"])


# ============ VERIFICATION ============
def try_import(module_name: str, test_file: Path | None = None) -> tuple[bool, str | None]:
    """Import a module and run its test file if provided. Returns (ok, error)."""
    if test_file and test_file.exists():
        cmd = [sys.executable, "-m", "pytest", str(test_file), "-q", "--timeout=30", "-W", "ignore"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=BASE)
        if "passed" in r.stdout:
            ok = True
            msg = None
        else:
            ok = False
            msg = r.stderr[-500:] or r.stdout[-500:]
    else:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return False, "module not found"
        try:
            importlib.import_module(module_name)
            ok = True
            msg = None
        except Exception as e:
            ok = False
            msg = str(e)
    return ok, msg


# ============ CORE EXECUTOR ============
def run_phase_builder(phase: int, task: str) -> str | None:
    """Dispatch to the phase builder. Returns None if skipped."""
    builder = getattr(_builders, f"build_phase_{phase}_{task}", None)
    if builder is None:
        return "no builder"
    return builder()


def execute_one(phase: int, task: str) -> str:
    """Try to implement a single task. Returns status: done|skipped|error."""
    state["started"].append(f"{phase}:{task}")
    save_state(state)
    mod = f"astrovox.phases.phase{phase}_{task}"
    test = BASE / "tests" / "phases" / f"test_{phase}_{task}.py"
    try:
        builder = getattr(_builders, f"build_phase_{phase}_{task}", None)
        if builder is None:
            raise RuntimeError("no builder")
        result = builder()
        if result is None:
            raise RuntimeError("builder skipped")
        ok, msg = try_import(mod, test)
        if ok:
            state["done"].append(f"{phase}:{task}")
            return "done"
        raise RuntimeError(msg or "verification failed")
    except Exception:
        err = traceback.format_exc().splitlines()[-1].strip()
        state["skipped"].append({"phase": phase, "task": task, "error": err})
        return "skipped"
    finally:
        state["last_run"] = f"{phase}:{task}"
        save_state(state)


def run_batch() -> dict:
    """Execute up to BATCH_SIZE tasks in a full sweep of all phases."""
    state["runs"] += 1
    results = []
    done, skipped, started = [], [], []
    for phase, name, tasks in PHASES:
        for task in tasks:
            key = f"{phase}:{task}"
            if key in state["done"]:
                continue
            if len(done) >= BATCH_SIZE:
                break
            status = execute_one(phase, task)
            (done if status == "done" else skipped).append(key)
    return {"done": done, "skipped": skipped}


def main(argv: list | None = None) -> None:
    global state
    state = load_state()
    args = argv if argv is not None else sys.argv[1:]
    stop = "--stop" in args
    batch = next((int(x.split("=")[1]) for x in args if x.startswith("--batch=")), BATCH_SIZE)
    phase_filter = next((int(x.split("=")[1]) for x in args if x.startswith("--phase=")), None)
    if phase_filter is not None:
        PHASES[:] = [(p, n, t) for p, n, t in PHASES if p == phase_filter]
    max_runs = next((int(x.split("=")[1]) for x in args if x.startswith("--max-runs=")), None)
    runs = 0
    while not stop:
        runs += 1
        done_keys = set(state["done"])
        remaining = sum(1 for p, n, t in PHASES for t in t if f"{p}:{t}" not in done_keys)
        print(f"\n=== Astrovox executor run #{runs} (batch={batch}) ===")
        print(f"Done: {len(done_keys)}  Skipped: {len(state['skipped'])}  Remaining: {remaining}")
        if remaining == 0:
            print("All phases complete. Looping again...")
        res = run_batch()
        if res["done"]:
            print(f"  done: {res['done']}")
        if res["skipped"]:
            print(f"  skipped: {res['skipped']}")
        save_state(state)
        if max_runs is not None and runs >= max_runs:
            print(f"\nReached max runs ({max_runs}). Stopping.")
            break


if __name__ == "__main__":
    main()
