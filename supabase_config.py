from supabase import create_client

url = "https://dowinoownpxfmowxltuw.supabase.co"
key = "YOUR_PUBLISHABLE_KEY"

supabase = create_client(url, key)

print("Supabase Connected Successfully 🚀")