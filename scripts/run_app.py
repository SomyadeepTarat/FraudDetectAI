import subprocess
import sys
from pathlib import Path


def main() -> None:

    project_root = Path(__file__).resolve().parents[1]
    app_path = project_root / "app" / "streamlit_app.py"

    if not app_path.exists():
        raise FileNotFoundError(f"Streamlit app not found: {app_path}")

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
    ]

    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()