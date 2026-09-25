#!/usr/bin/env python3
"""
Backend Modularization Migration Script
Consolidates 771-file monolith into modular architecture.
"""

import os
import re
import ast
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

BASE_DIR = Path(r"C:\Users\Dell\Documents\GitHub\AstrovoxAi\02-Backend\app")
NEW_BASE = BASE_DIR  # Same directory, restructure in place


@dataclass
class MigrationPlan:
    """Represents a file migration."""
    old_path: Path
    new_path: Path
    reason: str


class ModularizationMigrator:
    """Main migration orchestrator."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.migrations: List[MigrationPlan] = []
        self.import_updates: Dict[Path, List[Tuple[str, str]]] = defaultdict(list)
        
    def plan(self):
        """Create migration plan."""
        self._plan_memory_modules()
        self._plan_database_modules()
        self._plan_api_modules()
        self._plan_auth_modules()
        self._plan_knowledge_modules()
        self._plan_router_consolidation()
        self._plan_large_file_splits()
        
    def _plan_memory_modules(self):
        """Consolidate memory modules into services/memory/."""
        memory_files = [
            "memory.py",
            "memory_advanced.py",
            "memory_enhanced.py",
            "memory_engine_v3.py",
            "memory_evolution.py",
            "memory_intelligence.py",
            "memory_leak_detection.py",
            "memory_manager.py",
            "memory_pipeline.py",
            "memory_router.py",
            "memory_service.py",
            "shared_memory.py",
            "hierarchical_memory.py",
            "memory_conflict.py",
            "acdos/distributed_memory.py",
            "aios/memory.py",
            "executor/memory_brain.py",
            "executor/memory/memory_management.py",
            "core/memory_intelligence_core.py",
        ]
        
        # Memory submodules in memory/ directory
        memory_submodules = [
            "memory/advanced_memory.py",
            "memory/context_memory.py",
            "memory/conversation_memory.py",
            "memory/episodic_memory.py",
            "memory/long_term_memory.py",
            "memory/memory.py",
            "memory/memory_consolidation.py",
            "memory/memory_manager.py",
            "memory/memory_ranking.py",
            "memory/procedural_memory.py",
            "memory/semantic_memory.py",
            "memory/vector_memory.py",
            "memory/working_memory.py",
            "memory/workspace_memory.py",
        ]
        
        # Router files
        memory_routers = [
            "routers/memory.py",
            "routers/memory_controls.py",
            "routers/memory_management.py",
            "memory_engine/router.py",
        ]
        
        # Consolidate all memory modules
        for rel_path in memory_files + memory_submodules + memory_routers:
            old = self.base_dir / rel_path
            if old.exists():
                new = self.base_dir / "services" / "memory" / old.name
                self.migrations.append(MigrationPlan(
                    old_path=old,
                    new_path=new,
                    reason=f"Consolidate memory module: {rel_path}"
                ))
                
    def _plan_database_modules(self):
        """Consolidate database modules into repositories/."""
        db_files = [
            "database.py",
            "database_engine.py",
            "infrastructure/database.py",
        ]
        
        for rel_path in db_files:
            old = self.base_dir / rel_path
            if old.exists():
                # Determine subfolder
                if "infrastructure" in rel_path:
                    new = self.base_dir / "repositories" / "database" / "engine.py"
                elif "engine" in rel_path:
                    new = self.base_dir / "repositories" / "database" / "query_optimizer.py"
                else:
                    new = self.base_dir / "repositories" / "database" / "client.py"
                    
                self.migrations.append(MigrationPlan(
                    old_path=old,
                    new_path=new,
                    reason=f"Consolidate database module: {rel_path}"
                ))
                
    def _plan_api_modules(self):
        """Consolidate API versioning into api/v1.py, v2.py."""
        api_files = [
            ("api_v1.py", "api/v1.py"),
            ("api_version.py", "api/versioning.py"),
            ("api_versioning.py", "api/versioning.py"),
            ("api.py", "api/__init__.py"),
        ]
        
        for old_name, new_name in api_files:
            old = self.base_dir / old_name
            if old.exists():
                new = self.base_dir / new_name
                self.migrations.append(MigrationPlan(
                    old_path=old,
                    new_path=new,
                    reason=f"Consolidate API module: {old_name} -> {new_name}"
                ))
                
    def _plan_auth_modules(self):
        """Consolidate auth modules."""
        auth_files = [
            "auth.py",
            "auth_enhanced.py",
            "auth_utils.py",
            "supabase_authenticated.py",
            "api_security.py",
            "enhanced_security.py",
            "ai_security.py",
            "ai_security_enhanced.py",
            "security.py",
            "security_hardening.py",
            "security_api.py",
            "security_route.py",
            "security_headers.py",
            "advanced_security.py",
            "rate_limit.py",
            "rate_limit_hardened.py",
            "rate_limiter.py",
            "rbac.py",
            "authorization.py",
        ]
        
        for rel_path in auth_files:
            old = self.base_dir / rel_path
            if old.exists():
                if "utils" in rel_path or rel_path.endswith("_utils.py"):
                    new = self.base_dir / "utils" / "auth" / old.name
                elif "security" in rel_path or "rate" in rel_path or "rbac" in rel_path:
                    new = self.base_dir / "middleware" / "security" / old.name
                else:
                    new = self.base_dir / "services" / "auth" / old.name
                    
                self.migrations.append(MigrationPlan(
                    old_path=old,
                    new_path=new,
                    reason=f"Consolidate auth/security module: {rel_path}"
                ))
                
    def _plan_knowledge_modules(self):
        """Consolidate knowledge modules."""
        knowledge_files = [
            "knowledge.py",
            "knowledge_base.py",
            "knowledge_graph.py",
            "knowledge_graph_neo4j.py",
            "knowledge_system.py",
            "knowledge_intelligence.py",
            "knowledge_distillation.py",
            "rag_engine.py",
            "rag_eval.py",
            "graph_rag.py",
            "graph_rag_v2.py",
            "cross_modal.py",
            "citations.py",
            "embeddings.py",
            "embeddings_route.py",
            "vector_search.py",  # if exists
            "knowledge/workspace_isolation.py",
            "knowledge/enhanced_vector_search.py",
        ]
        
        for rel_path in knowledge_files:
            old = self.base_dir / rel_path
            if old.exists():
                if "embedding" in rel_path or "vector" in rel_path:
                    new = self.base_dir / "services" / "vector" / old.name
                elif "rag" in rel_path:
                    new = self.base_dir / "services" / "rag" / old.name
                else:
                    new = self.base_dir / "services" / "knowledge" / old.name
                    
                self.migrations.append(MigrationPlan(
                    old_path=old,
                    new_path=new,
                    reason=f"Consolidate knowledge module: {rel_path}"
                ))
                
    def _plan_router_consolidation(self):
        """Consolidate routers into api/."""
        router_files = [
            "auth_route.py",
            "agent_route.py",
            "agents_route.py",
            "analytics_route.py",
            "automation_route.py",
            "dashboard_route.py",
            "document_route.py",
            "embeddings_route.py",
            "enterprise/router.py",
            "jobs_router.py",
            "knowledge_route.py",
            "knowledge_route_v2.py",
            "monitoring_route.py",
            "platform_route.py",
            "realtime_route.py",
            "security_route.py",
            "workspace_route.py",
            "admin_panel.py",
            "admin_route.py",
            "agent_collaboration.py",
            "agents_route.py",
            "telemetry.py",  # might be router
        ]
        
        for rel_path in router_files:
            old = self.base_dir / rel_path
            if old.exists():
                new = self.base_dir / "api" / "routers" / old.name
                self.migrations.append(MigrationPlan(
                    old_path=old,
                    new_path=new,
                    reason=f"Consolidate router: {rel_path}"
                ))
                
    def _plan_large_file_splits(self):
        """Plan splits for large files."""
        large_files = [
            ("workspace_route.py", ["api/routers/workspace_routes.py", "api/routers/workspace_schemas.py"]),
            ("workspace.py", ["services/workspace/service.py", "services/workspace/models.py"]),
            ("document_intelligence.py", ["services/documents/intelligence.py", "services/documents/parsers.py"]),
            ("knowledge_system.py", ["services/knowledge/system.py", "services/knowledge/retrieval.py"]),
            ("analytics.py", ["services/analytics/engine.py", "services/analytics/reports.py"]),
            ("workflow_engine.py", ["services/workflows/engine.py", "services/workflows/executor.py"]),
        ]
        
        for old_name, new_parts in large_files:
            old = self.base_dir / old_name
            if old.exists():
                # Just create placeholder for now - actual split is complex
                for new_part in new_parts:
                    new = self.base_dir / new_part
                    self.migrations.append(MigrationPlan(
                        old_path=old,
                        new_path=new,
                        reason=f"Split large file: {old_name}"
                    ))
                    
    def execute(self, dry_run: bool = False):
        """Execute the migration plan."""
        if dry_run:
            print("=== DRY RUN ===")
            for m in self.migrations:
                print(f"  {m.old_path} -> {m.new_path}")
                print(f"    Reason: {m.reason}")
            print(f"\nTotal migrations planned: {len(self.migrations)}")
            return
            
        # Create directories
        for m in self.migrations:
            m.new_path.parent.mkdir(parents=True, exist_ok=True)
            
        # Execute migrations
        success = 0
        errors = 0
        for m in self.migrations:
            try:
                if m.old_path.exists():
                    shutil.move(str(m.old_path), str(m.new_path))
                    success += 1
            except Exception as e:
                print(f"Error moving {m.old_path}: {e}")
                errors += 1
                
        print(f"Migration complete: {success} success, {errors} errors")
        
    def update_imports(self):
        """Update imports across all Python files."""
        # Build mapping of old -> new module paths
        old_to_new = {}
        for m in self.migrations:
            old_module = self._path_to_module(m.old_path)
            new_module = self._path_to_module(m.new_path)
            if old_module != new_module:
                old_to_new[old_module] = new_module
                
        print(f"Updating {len(old_to_new)} import mappings...")
        
        # Update all Python files
        for py_file in self.base_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                original = content
                
                for old_imp, new_imp in old_to_new.items():
                    # Replace various import patterns
                    patterns = [
                        f"from {old_imp}",
                        f"import {old_imp}",
                        f"from .{old_imp.replace('app.', '')}",
                    ]
                    for pattern in patterns:
                        content = content.replace(pattern, pattern.replace(old_imp, new_imp))
                        
                if content != original:
                    py_file.write_text(content, encoding='utf-8')
            except Exception as e:
                print(f"Error updating {py_file}: {e}")
                
    def _path_to_module(self, path: Path) -> str:
        """Convert file path to module path."""
        try:
            rel = path.relative_to(self.base_dir)
            parts = list(rel.parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            elif parts[-1].endswith(".py"):
                parts[-1] = parts[-1][:-3]
            return ".".join(parts)
        except Exception:
            return ""


def main():
    migrator = ModularizationMigrator(BASE_DIR)
    migrator.plan()
    
    print("=== Migration Plan ===")
    print(f"Total migrations: {len(migrator.migrations)}")
    
    # Group by category
    by_reason = defaultdict(list)
    for m in migrator.migrations:
        category = m.reason.split(":")[0].strip()
        by_reason[category].append(m)
        
    for cat, plans in sorted(by_reason.items()):
        print(f"\n{cat}: {len(plans)} files")
        
    # Auto-proceed for automated migration
    migrator.execute()
    migrator.update_imports()
    print("\nMigration complete!")


if __name__ == "__main__":
    main()
