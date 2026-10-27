import os, sys, traceback
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("JWT_SECRET_KEY", "dev-secret-key-min-32-chars-xxxxxxxx")
sys.path.insert(0, "02-Backend")
try:
    import app.main
    print("app.main OK")
except Exception:
    traceback.print_exc()
