import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    app = root / "app.py"
    if not app.is_file():
        print("app.py not found at repository root.")
        sys.exit(1)
    raise SystemExit(
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(app)],
            cwd=str(root),
        ).returncode
    )


if __name__ == "__main__":
    main()
