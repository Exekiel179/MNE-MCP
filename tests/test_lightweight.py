"""Importing the server must not eagerly import the scientific stack."""

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
        print("LIGHT-OK")
        """)
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert "LIGHT-OK" in proc.stdout, (
        f"server imported a heavy package at load time.\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
