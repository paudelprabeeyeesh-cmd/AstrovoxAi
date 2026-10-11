"""Database accessor for the analytics package.

Analytics modules use ``from .database import get_db``; this module is the
local alias for the shared client accessor in
``app.repositories.database.client`` so analytics code does not have to
reach across the package tree to get a connection.
"""

from app.repositories.database.client import get_db

__all__ = ["get_db"]
