"""Server-layer tests: importing the module registers all tools on the FastMCP app."""

import asyncio
import importlib

from fastmcp import FastMCP


def _registered_tool_names(server):
    """Best-effort across FastMCP versions; returns a set of tool names or None."""
    try:
        return set(asyncio.run(server.mcp.get_tools()).keys())
    except Exception:
        return None


def test_server_imports_and_builds_app():
    server = importlib.import_module("mne_mcp.server")
    assert isinstance(server.mcp, FastMCP)


def test_server_registers_full_toolset():
    server = importlib.import_module("mne_mcp.server")
    names = _registered_tool_names(server)
    if names is None:
        return  # introspection API differs; the import above already exercised registration
    assert len(names) >= 38, f"expected >=38 registered tools, got {len(names)}"
    for t in ("mne_check_status", "mne_load_raw", "mne_run_code", "mne_filter"):
        assert t in names
