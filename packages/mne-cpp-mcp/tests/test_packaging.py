import subprocess
import sys


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
    )
    assert result.returncode == 0, result.stderr
