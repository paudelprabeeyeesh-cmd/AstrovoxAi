import os

from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client
except Exception:  # pragma: no cover - allows tests to import without the package
    create_client = None

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or "https://dowinoownpxfmowxltuw.supabase.co"
SUPABASE_SERVICE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY") or "sb_publishable_w3hs3ZGJjH_QKleb7cmQCw_OnI5vbWS"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY) if create_client else None