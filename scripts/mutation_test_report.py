
import subprocess
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "02-Backend"


def main() -> int:
    print("Running mutation testing results...")
    result = subprocess.run(
        [sys.executable, "-m", "mutmut", "results", "--config", str(backend_dir / "mutmut.yaml")],
        cwd=backend_dir,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
