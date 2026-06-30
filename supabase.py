from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("https://dowinoownpxfmowxltuw.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("sb_publishable_w3hs3ZGJjH_QKleb7cmQCw_OnI5vbWS")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)