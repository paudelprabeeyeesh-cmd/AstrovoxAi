import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
print("DEBUG conftest sys.path:", sys.path[:3])
print("DEBUG conftest backend_dir:", backend_dir)
