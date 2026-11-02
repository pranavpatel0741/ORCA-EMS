"""Launch v2 with its own theme, independently of the original dashboard."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(Path(__file__).with_name("streamlit_app.py")),
            "--theme.base=light",
            "--theme.primaryColor=#ed713d",
            "--theme.backgroundColor=#f5f6f8",
            "--theme.secondaryBackgroundColor=#ffffff",
            "--theme.textColor=#1d2b40",
            *sys.argv[1:],
        ],
        check=True,
    )
