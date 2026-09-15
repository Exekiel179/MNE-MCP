import subprocess
import sys
import os
from pathlib import Path


def test_no_scientific_imports():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import mne_cpp_mcp.server; assert not ({'mne', 'numpy', 'scipy'} & set(sys.modules))",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")},
    )
    assert result.returncode == 0, result.stderr
