"""Pytest configuration for the canonical FastAPI backend.

Sets dummy Supabase credentials before the app is imported so the shared
client can be constructed without real secrets, and exposes the backend
package on sys.path.
"""

import os
import sys
from pathlib import Path

# Backend root (02-Backend) so `import app.main` resolves.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Dummy creds: the health/readiness/root routes never call Supabase, but the
# shared client is created at import time and requires these to be set.
os.environ.setdefault("VITE_SUPABASE_URL", "https://dummy.supabase.co")
os.environ.setdefault("VITE_SUPABASE_ANON_KEY", "dummy-anon-key")
