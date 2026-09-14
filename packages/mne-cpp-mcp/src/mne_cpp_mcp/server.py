"""stdio MCP entrypoint. FIFF inspection stays in native processes."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .backend import Backend, BackendError, FileParameters, InspectParameters, ToolName

mcp = FastMCP("mne_cpp_mcp")
_backend = None
READ = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}


def backend() -> Backend:
    global _backend
    if _backend is None:
        _backend = Backend.from_environment()
    return _backend


@mcp.tool(annotations=READ)
async def mne_cpp_check_status() -> dict[str, Any]:
    """Verify native executables and version; report missing installation without installing anything."""
    try:
        return await backend().status()
    except BackendError as exc:
        return {"ready": False, "error": str(exc)}


@mcp.tool(annotations=READ)
async def mne_cpp_get_help(tool: ToolName) -> dict[str, Any]:
    """Read installed official help. Only the two allowlisted native inspection tools can be executed."""
    return await backend().run(tool, ["--help"], help_call=True)


@mcp.tool(annotations=READ)
async def mne_cpp_inspect_fiff(params: InspectParameters) -> dict[str, Any]:
    """Inspect FIFF structure with native MNE-CPP; blocks_only avoids detailed metadata by default."""
    return await backend().inspect(params)


@mcp.tool(annotations=READ)
async def mne_cpp_read_metadata(params: FileParameters) -> dict[str, Any]:
    """Read sampling and Nyquist frequency via native FIFF tags; not a signal quality assessment."""
    return await backend().metadata(params)


@mcp.tool(annotations=READ)
async def mne_cpp_evoked_summary(params: FileParameters) -> dict[str, Any]:
    """Read native evoked dataset counts, nave, time range and channel types; not statistical analysis."""
    return await backend().evoked_summary(params)


def main():
    parser = argparse.ArgumentParser(
        description="MNE-CPP native inspection MCP preview"
    )
    parser.add_argument(
        "command", choices=["serve", "status", "skill-path"], nargs="?", default="serve"
    )
    args = parser.parse_args()
    if args.command == "skill-path":
        bundled = Path(__file__).parent / "_bundled" / "skills" / "mne-cpp-analyst"
        source = Path(__file__).parents[2] / "skills" / "mne-cpp-analyst"
        path = bundled if bundled.is_dir() else source
        if not (path / "SKILL.md").is_file():
            parser.error("Companion skill missing; reinstall this package")
        print(path)
        return
    if args.command == "status":
        result = asyncio.run(mne_cpp_check_status())
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["ready"] else 1)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
