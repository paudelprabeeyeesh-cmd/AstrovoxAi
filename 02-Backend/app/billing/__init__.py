"""Billing package initialiser.

The billing implementation lives in ``app/billing.py``. A package directory
shadows a sibling module of the same name, so ``import app.billing``
reaches this file, and ``from app.billing import handle_stripe_webhook``
raised ImportError. The Stripe webhook path was therefore silently dead
despite the implementation being present and tested.

The legacy module is registered in ``sys.modules`` under the ``app.billing``
name so every import path *and* every ``patch("app.billing.<name>")``
target resolves to the same module object. Re-exporting instead of
replacing the sys.modules entry would leave patches applied to the package
namespace while the functions keep reading their own module globals, which
is how this path silently stopped working.
"""
from __future__ import annotations

import importlib.util
import os
import sys

_HERE = os.path.dirname(__file__)
# 02-Backend/app/billing/__init__.py -> 02-Backend/app/billing.py
_LEGACY = os.path.join(os.path.dirname(_HERE), "billing.py")

if os.path.exists(_LEGACY):
    _spec = importlib.util.spec_from_file_location("app.billing", _LEGACY)
    _legacy = importlib.util.module_from_spec(_spec)
    sys.modules["app.billing"] = _legacy
    _spec.loader.exec_module(_legacy)
    __path__ = list(_spec.submodule_search_locations or [])
else:  # pragma: no cover - defensive
    __path__ = []
