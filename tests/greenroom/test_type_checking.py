"""Run mypy static type checker as part of the test suite."""

import subprocess
import sys
from pathlib import Path


def test_mypy():
    """Run mypy on src/greenroom/ and fail if any type errors are found."""
    project_root = Path(__file__).parent.parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "src/greenroom/"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    assert result.returncode == 0, (
        f"mypy found type errors:\n{result.stdout}\n{result.stderr}"
    )
