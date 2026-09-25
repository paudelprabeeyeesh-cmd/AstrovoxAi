#!/usr/bin/env python3
"""
Comprehensive import fixer for backend modularization.
Fixes relative imports based on new file locations.
"""

import ast
import re
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(r"C:\Users\Dell\Documents\GitHub\AstrovoxAi\02-Backend\app")


# Module path mappings (old -> new)
MODULE_MAPPINGS = {
    # Database
    "database": "repositories.database.client",
    "database_engine": "repositories.database.query_optimizer",
    "infrastructure.database": "repositories.database.engine",
    
    # Memory
    "memory": "services.memory.memory",
    "memory_advanced": "services.memory.memory_advanced",
    "memory_enhanced": "services.memory.memory_enhanced",
    "memory_engine_v3": "services.memory.memory_engine_v3",
    "memory_evolution": "services.memory.memory_evolution",
    "memory_intelligence": "services.memory.memory_intelligence",
    "memory_leak_detection": "services.memory.memory_leak_detection",
    "memory_manager": "services.memory.memory_manager",
    "memory_pipeline": "services.memory.memory_pipeline",
    "memory_router": "services.memory.memory_router",
    "memory_service": "services.memory.memory_service",
    "shared_memory": "services.memory.shared_memory",
    "hierarchical_memory": "services.memory.hierarchical_memory",
    "memory_conflict": "services.memory.memory_conflict",
    "acdos.distributed_memory": "services.memory.distributed_memory",
    "aios.memory": "services.memory.aios_memory",
    "executor.memory_brain": "services.memory.memory_brain",
    "executor.memory.memory_management": "services.memory.memory_management",
    "core.memory_intelligence_core": "services.memory.memory_intelligence_core",
    "memory.advanced_memory": "services.memory.advanced_memory",
    "memory.context_memory": "services.memory.context_memory",
    "memory.conversation_memory": "services.memory.conversation_memory",
    "memory.episodic_memory": "services.memory.episodic_memory",
    "memory.long_term_memory": "services.memory.long_term_memory",
    "memory.memory": "services.memory.memory",
    "memory.memory_consolidation": "services.memory.memory_consolidation",
    "memory.memory_manager": "services.memory.memory_manager",
    "memory.memory_ranking": "services.memory.memory_ranking",
    "memory.procedural_memory": "services.memory.procedural_memory",
    "memory.semantic_memory": "services.memory.semantic_memory",
    "memory.vector_memory": "services.memory.vector_memory",
    "memory.working_memory": "services.memory.working_memory",
    "memory.workspace_memory": "services.memory.workspace_memory",
    
    # Auth
    "auth": "services.auth.auth",
    "auth_enhanced": "services.auth.auth_enhanced",
    "auth_utils": "utils.auth.auth_utils",
    "supabase_authenticated": "services.auth.supabase_authenticated",
    "api_security": "middleware.security.api_security",
    "enhanced_security": "middleware.security.enhanced_security",
    "ai_security": "middleware.security.ai_security",
    "ai_security_enhanced": "middleware.security.ai_security_enhanced",
    "security": "middleware.security.security",
    "security_hardening": "middleware.security.security_hardening",
    "security_api": "middleware.security.security_api",
    "security_route": "api.routers.auth.security_route",
    "security_headers": "middleware.security.security_headers",
    "advanced_security": "middleware.security.advanced_security",
    "rate_limit": "middleware.security.rate_limit",
    "rate_limit_hardened": "middleware.security.rate_limit_hardened",
    "rate_limiter": "middleware.security.rate_limiter",
    "rbac": "middleware.security.rbac",
    "authorization": "middleware.security.authorization",
    
    # Knowledge
    "knowledge": "services.knowledge.knowledge",
    "knowledge_base": "services.knowledge.knowledge_base",
    "knowledge_graph": "services.knowledge.knowledge_graph",
    "knowledge_graph_neo4j": "services.knowledge.knowledge_graph_neo4j",
    "knowledge_system": "services.knowledge.knowledge_system",
    "knowledge_intelligence": "services.knowledge.knowledge_intelligence",
    "knowledge_distillation": "services.knowledge.knowledge_distillation",
    "rag_engine": "services.rag.rag_engine",
    "rag_eval": "services.rag.rag_eval",
    "graph_rag": "services.rag.graph_rag",
    "graph_rag_v2": "services.rag.graph_rag_v2",
    "cross_modal": "services.knowledge.cross_modal",
    "citations": "services.knowledge.citations",
    "embeddings": "services.vector.embeddings",
    "embeddings_route": "services.vector.embeddings_route",
    "knowledge.workspace_isolation": "services.knowledge.workspace_isolation",
    "knowledge.enhanced_vector_search": "services.knowledge.enhanced_vector_search",
    
    # API
    "api_v1": "api.v1",
    "api_version": "api.versioning",
    "api_versioning": "api.versioning",
    
    # Routers
    "agent_route": "api.routers.agent_route",
    "agents_route": "api.routers.agents_route",
    "analytics_route": "api.routers.analytics_route",
    "automation_route": "api.routers.automation_route",
    "dashboard_route": "api.routers.dashboard_route",
    "document_route": "api.routers.document_route",
    "enterprise.router": "api.routers.router",
    "jobs_router": "api.routers.jobs_router",
    "knowledge_route": "api.routers.knowledge_route",
    "knowledge_route_v2": "api.routers.knowledge_route_v2",
    "monitoring_route": "api.routers.monitoring_route",
    "platform_route": "api.routers.platform_route",
    "realtime_route": "api.routers.realtime_route",
    "workspace_route": "api.routers.workspace_route",
    "admin_panel": "api.routers.admin_panel",
    "admin_route": "api.routers.admin_route",
    "agent_collaboration": "api.routers.agent_collaboration",
    "agents_route": "api.routers.agents_route",
    "memory_engine.router": "api.routers.memory.router",
    "routers.memory": "api.routers.memory.memory",
    "routers.memory_controls": "api.routers.memory.memory_controls",
    "routers.memory_management": "api.routers.memory.memory_management",
}


def get_module_path(file_path: Path) -> str:
    """Get the module path for a file."""
    try:
        rel = file_path.relative_to(BASE_DIR)
        parts = list(rel.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        elif parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        return ".".join(parts)
    except Exception:
        return ""


def resolve_import(current_file: Path, import_module: str, level: int) -> str:
    """Resolve a relative import to an absolute module path."""
    if level == 0:
        return import_module
    
    # Calculate the base package from current file location
    rel_parts = list(current_file.relative_to(BASE_DIR).parts)
    if rel_parts[-1].endswith(".py"):
        rel_parts = rel_parts[:-1]
    if rel_parts[-1] == "__pycache__":
        rel_parts = rel_parts[:-1]
    
    # Go up (level - 1) directories
    if level > 1:
        base_parts = rel_parts[:-(level - 1)]
    else:
        base_parts = rel_parts
    
    # Handle edge case: file at root level
    if not base_parts:
        base_parts = []
    
    # Append the imported module
    if import_module:
        base_parts.extend(import_module.split("."))
    
    return ".".join(base_parts) if base_parts else (import_module or "")


def fix_imports_in_file(file_path: Path):
    """Fix imports in a single file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original = content
        
        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return False
        
        replacements = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module is None and node.level == 0:
                    continue
                    
                old_import = node.module or ""
                level = node.level
                
                # Resolve to absolute module path
                abs_module = resolve_import(file_path, old_import, level)
                
                # Check if we have a mapping for this
                if abs_module in MODULE_MAPPINGS:
                    new_module = MODULE_MAPPINGS[abs_module]
                    
                    # Calculate new relative import
                    current_module = get_module_path(file_path)
                    current_parts = current_module.split(".")
                    new_parts = new_module.split(".")
                    
                    # Find common prefix
                    common = 0
                    for i in range(min(len(current_parts), len(new_parts))):
                        if current_parts[i] == new_parts[i]:
                            common += 1
                        else:
                            break
                    
                    # Calculate dots needed
                    dots = "." * (len(current_parts) - common)
                    remaining = ".".join(new_parts[common:])
                    
                    if remaining:
                        new_import_str = f"{dots}{remaining}"
                    else:
                        new_import_str = dots
                    
                    # Build old import string
                    old_prefix = "." * level
                    old_import_str = f"{old_prefix}{old_import}"
                    
                    replacements.append((old_import_str, new_import_str))
        
        # Apply replacements
        for old_str, new_str in replacements:
            # Use regex to be more precise
            pattern = rf'\bfrom\s+{re.escape(old_str)}\b'
            content = re.sub(pattern, f'from {new_str}', content)
        
        if content != original:
            file_path.write_text(content, encoding='utf-8')
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False


def main():
    py_files = list(BASE_DIR.rglob("*.py"))
    print(f"Fixing imports in {len(py_files)} files...")
    
    updated = 0
    for py_file in py_files:
        if fix_imports_in_file(py_file):
            updated += 1
            if updated % 50 == 0:
                print(f"  Updated {updated} files...")
    
    print(f"Fixed imports in {updated} files")


if __name__ == "__main__":
    main()
