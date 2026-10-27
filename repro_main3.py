import os, sys, warnings
warnings.filterwarnings("ignore")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("JWT_SECRET_KEY", "dev-secret-key")
sys.path.insert(0, "02-Backend")
print("STARTING_IMPORT", flush=True)
import app.main
print("app.main OK", flush=True)
