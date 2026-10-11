"""Compatibility shim: ``app.services.rag.service`` holds the implementation.

The class moved here because a package (``app/services/rag/``) and a module
(``app/services/rag.py``) cannot share a name: the package wins the import,
so the old module path is now a thin re-export.
"""

from .service import RAGService

__all__ = ["RAGService"]