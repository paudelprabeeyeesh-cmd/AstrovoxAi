#!/usr/bin/env python3
"""
Simple but robust import fixer.
Does string-based replacement of old module names with new module names.
"""

import re
from pathlib import Path

BASE_DIR = Path(r"C:\Users\Dell\Documents\GitHub\AstrovoxAi\02-Backend\app")

# Simple module name replacements (old -> new)
REPLACEMENTS = [
    # Database
    ("from database import", "from repositories.database.client import"),
    ("from .database import", "from repositories.database.client import"),
    ("from ..database import", "from repositories.database.client import"),
    ("from database_engine import", "from repositories.database.query_optimizer import"),
    ("from .database_engine import", "from repositories.database.query_optimizer import"),
    ("from infrastructure.database import", "from repositories.database.engine import"),
    ("from .infrastructure.database import", "from repositories.database.engine import"),
    ("import database", "import repositories.database.client"),
    ("import database_engine", "import repositories.database.query_optimizer"),
    ("import infrastructure.database", "import repositories.database.engine"),
    
    # Memory - direct files
    ("from memory import", "from services.memory.memory import"),
    ("from .memory import", "from services.memory.memory import"),
    ("from memory_advanced import", "from services.memory.memory_advanced import"),
    ("from .memory_advanced import", "from services.memory.memory_advanced import"),
    ("from memory_enhanced import", "from services.memory.memory_enhanced import"),
    ("from .memory_enhanced import", "from services.memory.memory_enhanced import"),
    ("from memory_engine_v3 import", "from services.memory.memory_engine_v3 import"),
    ("from .memory_engine_v3 import", "from services.memory.memory_engine_v3 import"),
    ("from memory_evolution import", "from services.memory.memory_evolution import"),
    ("from .memory_evolution import", "from services.memory.memory_evolution import"),
    ("from memory_intelligence import", "from services.memory.memory_intelligence import"),
    ("from .memory_intelligence import", "from services.memory.memory_intelligence import"),
    ("from memory_leak_detection import", "from services.memory.memory_leak_detection import"),
    ("from .memory_leak_detection import", "from services.memory.memory_leak_detection import"),
    ("from memory_manager import", "from services.memory.memory_manager import"),
    ("from .memory_manager import", "from services.memory.memory_manager import"),
    ("from memory_pipeline import", "from services.memory.memory_pipeline import"),
    ("from .memory_pipeline import", "from services.memory.memory_pipeline import"),
    ("from memory_router import", "from services.memory.memory_router import"),
    ("from .memory_router import", "from services.memory.memory_router import"),
    ("from memory_service import", "from services.memory.memory_service import"),
    ("from .memory_service import", "from services.memory.memory_service import"),
    ("from shared_memory import", "from services.memory.shared_memory import"),
    ("from .shared_memory import", "from services.memory.shared_memory import"),
    ("from hierarchical_memory import", "from services.memory.hierarchical_memory import"),
    ("from .hierarchical_memory import", "from services.memory.hierarchical_memory import"),
    ("from memory_conflict import", "from services.memory.memory_conflict import"),
    ("from .memory_conflict import", "from services.memory.memory_conflict import"),
    ("from acdos.distributed_memory import", "from services.memory.distributed_memory import"),
    ("from .acdos.distributed_memory import", "from services.memory.distributed_memory import"),
    ("from aios.memory import", "from services.memory.aios_memory import"),
    ("from .aios.memory import", "from services.memory.aios_memory import"),
    ("from executor.memory_brain import", "from services.memory.memory_brain import"),
    ("from .executor.memory_brain import", "from services.memory.memory_brain import"),
    ("from executor.memory.memory_management import", "from services.memory.memory_management import"),
    ("from .executor.memory.memory_management import", "from services.memory.memory_management import"),
    ("from core.memory_intelligence_core import", "from services.memory.memory_intelligence_core import"),
    ("from .core.memory_intelligence_core import", "from services.memory.memory_intelligence_core import"),
    
    # Memory - submodules
    ("from memory.advanced_memory import", "from services.memory.advanced_memory import"),
    ("from .memory.advanced_memory import", "from services.memory.advanced_memory import"),
    ("from memory.context_memory import", "from services.memory.context_memory import"),
    ("from .memory.context_memory import", "from services.memory.context_memory import"),
    ("from memory.conversation_memory import", "from services.memory.conversation_memory import"),
    ("from .memory.conversation_memory import", "from services.memory.conversation_memory import"),
    ("from memory.episodic_memory import", "from services.memory.episodic_memory import"),
    ("from .memory.episodic_memory import", "from services.memory.episodic_memory import"),
    ("from memory.long_term_memory import", "from services.memory.long_term_memory import"),
    ("from .memory.long_term_memory import", "from services.memory.long_term_memory import"),
    ("from memory.memory import", "from services.memory.memory import"),
    ("from .memory.memory import", "from services.memory.memory import"),
    ("from memory.memory_consolidation import", "from services.memory.memory_consolidation import"),
    ("from .memory.memory_consolidation import", "from services.memory.memory_consolidation import"),
    ("from memory.memory_manager import", "from services.memory.memory_manager import"),
    ("from .memory.memory_manager import", "from services.memory.memory_manager import"),
    ("from memory.memory_ranking import", "from services.memory.memory_ranking import"),
    ("from .memory.memory_ranking import", "from services.memory.memory_ranking import"),
    ("from memory.procedural_memory import", "from services.memory.procedural_memory import"),
    ("from .memory.procedural_memory import", "from services.memory.procedural_memory import"),
    ("from memory.semantic_memory import", "from services.memory.semantic_memory import"),
    ("from .memory.semantic_memory import", "from services.memory.semantic_memory import"),
    ("from memory.vector_memory import", "from services.memory.vector_memory import"),
    ("from .memory.vector_memory import", "from services.memory.vector_memory import"),
    ("from memory.working_memory import", "from services.memory.working_memory import"),
    ("from .memory.working_memory import", "from services.memory.working_memory import"),
    ("from memory.workspace_memory import", "from services.memory.workspace_memory import"),
    ("from .memory.workspace_memory import", "from services.memory.workspace_memory import"),
    
    # Auth
    ("from auth import", "from services.auth.auth import"),
    ("from .auth import", "from services.auth.auth import"),
    ("from auth_enhanced import", "from services.auth.auth_enhanced import"),
    ("from .auth_enhanced import", "from services.auth.auth_enhanced import"),
    ("from auth_utils import", "from utils.auth.auth_utils import"),
    ("from .auth_utils import", "from utils.auth.auth_utils import"),
    ("from ..auth_utils import", "from utils.auth.auth_utils import"),
    ("from supabase_authenticated import", "from services.auth.supabase_authenticated import"),
    ("from .supabase_authenticated import", "from services.auth.supabase_authenticated import"),
    ("from api_security import", "from middleware.security.api_security import"),
    ("from .api_security import", "from middleware.security.api_security import"),
    ("from enhanced_security import", "from middleware.security.enhanced_security import"),
    ("from .enhanced_security import", "from middleware.security.enhanced_security import"),
    ("from ai_security import", "from middleware.security.ai_security import"),
    ("from .ai_security import", "from middleware.security.ai_security import"),
    ("from ai_security_enhanced import", "from middleware.security.ai_security_enhanced import"),
    ("from .ai_security_enhanced import", "from middleware.security.ai_security_enhanced import"),
    ("from security import", "from middleware.security.security import"),
    ("from .security import", "from middleware.security.security import"),
    ("from security_hardening import", "from middleware.security.security_hardening import"),
    ("from .security_hardening import", "from middleware.security.security_hardening import"),
    ("from security_api import", "from middleware.security.security_api import"),
    ("from .security_api import", "from middleware.security.security_api import"),
    ("from security_route import", "from api.routers.auth.security_route import"),
    ("from .security_route import", "from api.routers.auth.security_route import"),
    ("from security_headers import", "from middleware.security.security_headers import"),
    ("from .security_headers import", "from middleware.security.security_headers import"),
    ("from advanced_security import", "from middleware.security.advanced_security import"),
    ("from .advanced_security import", "from middleware.security.advanced_security import"),
    ("from rate_limit import", "from middleware.security.rate_limit import"),
    ("from .rate_limit import", "from middleware.security.rate_limit import"),
    ("from rate_limit_hardened import", "from middleware.security.rate_limit_hardened import"),
    ("from .rate_limit_hardened import", "from middleware.security.rate_limit_hardened import"),
    ("from rate_limiter import", "from middleware.security.rate_limiter import"),
    ("from .rate_limiter import", "from middleware.security.rate_limiter import"),
    ("from rbac import", "from middleware.security.rbac import"),
    ("from .rbac import", "from middleware.security.rbac import"),
    ("from authorization import", "from middleware.security.authorization import"),
    ("from .authorization import", "from middleware.security.authorization import"),
    
    # Knowledge
    ("from knowledge import", "from services.knowledge.knowledge import"),
    ("from .knowledge import", "from services.knowledge.knowledge import"),
    ("from knowledge_base import", "from services.knowledge.knowledge_base import"),
    ("from .knowledge_base import", "from services.knowledge.knowledge_base import"),
    ("from knowledge_graph import", "from services.knowledge.knowledge_graph import"),
    ("from .knowledge_graph import", "from services.knowledge.knowledge_graph import"),
    ("from knowledge_graph_neo4j import", "from services.knowledge.knowledge_graph_neo4j import"),
    ("from .knowledge_graph_neo4j import", "from services.knowledge.knowledge_graph_neo4j import"),
    ("from knowledge_system import", "from services.knowledge.knowledge_system import"),
    ("from .knowledge_system import", "from services.knowledge.knowledge_system import"),
    ("from knowledge_intelligence import", "from services.knowledge.knowledge_intelligence import"),
    ("from .knowledge_intelligence import", "from services.knowledge.knowledge_intelligence import"),
    ("from knowledge_distillation import", "from services.knowledge.knowledge_distillation import"),
    ("from .knowledge_distillation import", "from services.knowledge.knowledge_distillation import"),
    ("from rag_engine import", "from services.rag.rag_engine import"),
    ("from .rag_engine import", "from services.rag.rag_engine import"),
    ("from rag_eval import", "from services.rag.rag_eval import"),
    ("from .rag_eval import", "from services.rag.rag_eval import"),
    ("from graph_rag import", "from services.rag.graph_rag import"),
    ("from .graph_rag import", "from services.rag.graph_rag import"),
    ("from graph_rag_v2 import", "from services.rag.graph_rag_v2 import"),
    ("from .graph_rag_v2 import", "from services.rag.graph_rag_v2 import"),
    ("from cross_modal import", "from services.knowledge.cross_modal import"),
    ("from .cross_modal import", "from services.knowledge.cross_modal import"),
    ("from citations import", "from services.knowledge.citations import"),
    ("from .citations import", "from services.knowledge.citations import"),
    ("from embeddings import", "from services.vector.embeddings import"),
    ("from .embeddings import", "from services.vector.embeddings import"),
    ("from embeddings_route import", "from services.vector.embeddings_route import"),
    ("from .embeddings_route import", "from services.vector.embeddings_route import"),
    
    # API
    ("from api_v1 import", "from api.v1 import"),
    ("from .api_v1 import", "from api.v1 import"),
    ("from api_version import", "from api.versioning import"),
    ("from .api_version import", "from api.versioning import"),
    ("from api_versioning import", "from api.versioning import"),
    ("from .api_versioning import", "from api.versioning import"),
    
    # Routers
    ("from agent_route import", "from api.routers.agent_route import"),
    ("from .agent_route import", "from api.routers.agent_route import"),
    ("from agents_route import", "from api.routers.agents_route import"),
    ("from .agents_route import", "from api.routers.agents_route import"),
    ("from analytics_route import", "from api.routers.analytics_route import"),
    ("from .analytics_route import", "from api.routers.analytics_route import"),
    ("from automation_route import", "from api.routers.automation_route import"),
    ("from .automation_route import", "from api.routers.automation_route import"),
    ("from dashboard_route import", "from api.routers.dashboard_route import"),
    ("from .dashboard_route import", "from api.routers.dashboard_route import"),
    ("from document_route import", "from api.routers.document_route import"),
    ("from .document_route import", "from api.routers.document_route import"),
    ("from jobs_router import", "from api.routers.jobs_router import"),
    ("from .jobs_router import", "from api.routers.jobs_router import"),
    ("from knowledge_route import", "from api.routers.knowledge_route import"),
    ("from .knowledge_route import", "from api.routers.knowledge_route import"),
    ("from knowledge_route_v2 import", "from api.routers.knowledge_route_v2 import"),
    ("from .knowledge_route_v2 import", "from api.routers.knowledge_route_v2 import"),
    ("from monitoring_route import", "from api.routers.monitoring_route import"),
    ("from .monitoring_route import", "from api.routers.monitoring_route import"),
    ("from platform_route import", "from api.routers.platform_route import"),
    ("from .platform_route import", "from api.routers.platform_route import"),
    ("from realtime_route import", "from api.routers.realtime_route import"),
    ("from .realtime_route import", "from api.routers.realtime_route import"),
    ("from workspace_route import", "from api.routers.workspace_route import"),
    ("from .workspace_route import", "from api.routers.workspace_route import"),
    ("from admin_panel import", "from api.routers.admin_panel import"),
    ("from .admin_panel import", "from api.routers.admin_panel import"),
    ("from admin_route import", "from api.routers.admin_route import"),
    ("from .admin_route import", "from api.routers.admin_route import"),
    ("from agent_collaboration import", "from api.routers.agent_collaboration import"),
    ("from .agent_collaboration import", "from api.routers.agent_collaboration import"),
    
    # api/routers relative imports (continued)
    ("from ..utils.auth.auth_utils import", "from ...utils.auth.auth_utils import"),
    ("from .utils.auth.auth_utils import", "from ...utils.auth.auth_utils import"),
    ("from ..multi_agent import", "from ...multi_agent import"),
    ("from .multi_agent import", "from ...multi_agent import"),
    ("from ..workflow_engine import", "from ...workflow_engine import"),
    ("from .workflow_engine import", "from ...workflow_engine import"),
    ("from ..tool_execution import", "from ...tool_execution import"),
    ("from .tool_execution import", "from ...tool_execution import"),
    ("from ..dashboard import", "from ...dashboard import"),
    ("from .dashboard import", "from ...dashboard import"),
    ("from ..analytics import", "from ...analytics import"),
    ("from .analytics import", "from ...analytics import"),
    ("from ..agent import", "from ...agent import"),
    ("from .agent import", "from ...agent import"),
    ("from ..realtime import", "from ...realtime import"),
    ("from .realtime import", "from ...realtime import"),
    ("from ..tools import", "from ...tools import"),
    ("from .tools import", "from ...tools import"),
    ("from ..monitoring import", "from ...monitoring import"),
    ("from .monitoring import", "from ...monitoring import"),
    ("from ..document_intelligence import", "from ...document_intelligence import"),
    ("from .document_intelligence import", "from ...document_intelligence import"),
    ("from ..jobs import", "from ...jobs import"),
    ("from .jobs import", "from ...jobs import"),
    ("from ..events import", "from ...events import"),
    ("from .events import", "from ...events import"),
    ("from ..unified_platform import", "from ...unified_platform import"),
    ("from .unified_platform import", "from ...unified_platform import"),
    ("from ..cost_management import", "from ...cost_management import"),
    ("from .cost_management import", "from ...cost_management import"),
    ("from ..compliance import", "from ...compliance import"),
    ("from .compliance import", "from ...compliance import"),
    ("from ..ai_evaluation import", "from ...ai_evaluation import"),
    ("from .ai_evaluation import", "from ...ai_evaluation import"),
    ("from ..iam import", "from ...iam import"),
    ("from .iam import", "from ...iam import"),
    ("from ..security_audit import", "from ...security_audit import"),
    ("from .security_audit import", "from ...security_audit import"),
    ("from ..integrations import", "from ...integrations import"),
    ("from ..model import", "from ...model import"),
    ("from ..metrics import", "from ...metrics import"),
    ("from ..schemas import", "from ...schemas import"),
    ("from ..config import", "from ...config import"),
    ("from ..supabase_client import", "from ...repositories.database.supabase_client import"),
    
    # Memory-specific imports from submodules
    ("from .importance_scorer import", "from .services.memory.importance_scorer import"),
    ("from .retrieval_engine import", "from .services.memory.retrieval_engine import"),
    ("from .vector_store import", "from .services.memory.vector_store import"),
    ("from .engine import", "from .engine import"),  # memory engine
    ("from ..core.context_manager import", "from ...core.context_manager import"),
    ("from ..memory.memory_manager import", "from ...services.memory.memory_manager import"),
    ("from ..memory.semantic_memory import", "from ...services.memory.semantic_memory import"),
    ("from ..memory.episodic_memory import", "from ...services.memory.episodic_memory import"),
    
    # Middleware security imports
    ("from .middleware.security.security_hardening import", "from ..security_hardening import"),
    ("from .secure_executor import", "from ..secure_executor import"),
    ("from .services.auth.auth import", "from ..services.auth.auth import"),
    ("from .repositories.database.client import", "from ..repositories.database.client import"),
    
    # Memory router specific
    ("from .utils.auth.auth_utils import", "from ..utils.auth.auth_utils import"),
    
    # api/v1.py imports
    ("from .utils.auth.auth_utils import", "from ..utils.auth.auth_utils import"),
    ("from .multi_agent import", "from ..multi_agent import"),
    ("from .workflow_engine import", "from ..workflow_engine import"),
    ("from .tool_execution import", "from ..tool_execution import"),
    ("from .dashboard import", "from ..dashboard import"),
    ("from .model import", "from ..model import"),
    ("from .integrations import", "from ..integrations import"),
    
    # embedding router
    ("from .embedding.providers import", "from ..services.vector.providers import"),
    ("from .services.vector.embeddings import", "from ...services.vector.embeddings import"),
    
    # Fix .database imports in subdirectories
    ("from .database import", "from repositories.database.client import"),
    ("from ..database import", "from repositories.database.client import"),
    ("from ...database import", "from repositories.database.client import"),
    
    # supabase_client in repositories
    ("from .supabase_client import", "from .supabase_client import"),
    ("from ..supabase_client import", "from ...repositories.database.supabase_client import"),
    
    # Fix services imports
    ("from .repositories.database.client import", "from ..repositories.database.client import"),
    ("from .services.vector.embeddings import", "from ...services.vector.embeddings import"),
    ("from .services.knowledge.knowledge import", "from ...services.knowledge.knowledge import"),
    ("from .services.knowledge.knowledge_graph_neo4j import", "from ...services.knowledge.knowledge_graph_neo4j import"),
    ("from ..logging_config import", "from ...logging_config import"),
    ("from .documents import", "from ...documents import"),
    ("from .config import", "from ...config import"),
    ("from .providers.base import", "from ...providers.base import"),
    ("from .providers.factory import", "from ...providers.factory import"),
    ("from .middleware.security.security_hardening import", "from ...middleware.security.security_hardening import"),
    ("from .iam import", "from ...iam import"),
    ("from .metrics import", "from ...metrics import"),
    ("from .schemas import", "from ...schemas import"),
]


def fix_file(file_path: Path) -> bool:
    """Fix imports in a single file."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
        original = content
        
        for old_imp, new_imp in REPLACEMENTS:
            content = content.replace(old_imp, new_imp)
        
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
        if fix_file(py_file):
            updated += 1
    
    print(f"Fixed imports in {updated} files")


if __name__ == "__main__":
    main()
