"""
Proof that the MCP server runs in a lightweight shell.

The whole point of the on-demand backend is that importing the server must NOT
pull in the heavy scientific stack (numpy/scipy/matplotlib/mne/pandas/sklearn).
We verify that in a clean subprocess by installing an import blocker that raises
for those top-level packages, then importing the server modules. If any of them
were imported at module load, the import would fail and the subprocess would not
print the sentinel.
"""

import subprocess
import sys
import textwrap


def test_server_imports_without_scientific_stack():
    code = textwrap.dedent("""
        import sys
        import importlib.abc

        BLOCK = {"numpy", "scipy", "matplotlib", "mne", "pandas", "sklearn"}

        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, name, path=None, target=None):
                if name.split(".")[0] in BLOCK:
                    raise ImportError("blocked heavy import: " + name)
                return None

        sys.meta_path.insert(0, Blocker())

        import mne_mcp            # runs __init__ (numpy compat must be a no-op)
        import mne_mcp.server     # registers all tools; must stay light
        import mne_mcp.cli
        import mne_mcp.backend

        # The capability probe must not import the heavy stack either.
        assert mne_mcp.backend.backend_available() is False
        print("LIGHT-OK")
        """)
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert "LIGHT-OK" in proc.stdout, (
        f"server imported a heavy package at load time.\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
