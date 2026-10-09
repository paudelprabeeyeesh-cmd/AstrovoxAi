
import subprocess
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "02-Backend"


def main() -> int:
    print("Running mutation testing with mutmut...")
    result = subprocess.run(
        [sys.executable, "-m", "mutmut", "run", "--config", str(backend_dir / "mutmut.yaml")],
        cwd=backend_dir,
    )
    if result.returncode != 0:
        print("Mutation testing failed or found surviving mutations")
        return result.returncode
    print("Mutation testing passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
