"""Backwards-compatible re-export of the shared auth helpers.

The canonical implementation lives in :mod:`app.utils.auth.auth_utils`.
This module previously contained a second, *different* implementation of
``get_user_id_from_token`` (a JWT-validator version) that overwrote the
Supabase one, so which behaviour a caller got depended on import order, and
the file also referenced an undefined ``logger``. One definition now exists.
"""

from app.utils.auth.auth_utils import (
    get_current_user,
    get_user_id_from_token,
    security_scheme,
)

__all__ = ["get_current_user", "get_user_id_from_token", "security_scheme"]
