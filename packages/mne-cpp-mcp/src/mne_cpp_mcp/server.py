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
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("serve")
    commands.add_parser("status")
    commands.add_parser("skill-path")
    installer = commands.add_parser(
        "setup",
        help="Verify native tools, register selected clients and install the skill",
    )
    installer.add_argument(
        "--clients",
        help="Comma-separated: claude,codex,opencode; default: detect a single installed client",
    )
    installer.add_argument("--data-dir", required=True, type=Path)
    native = installer.add_mutually_exclusive_group()
    native.add_argument("--bin-dir", type=Path)
    native.add_argument(
        "--install-native",
        action="store_true",
        default=None,
        help="Explicitly use the managed runtime (already the default without --bin-dir or MNE_CPP_BIN_DIR)",
    )
    installer.add_argument("--native-dir", type=Path)
    installer.add_argument(
        "--archive", type=Path, help="Offline official ZIP; same SHA-256 verification"
    )
    installer.add_argument(
        "--check",
        action="store_true",
        help="Read-only preflight; never download or write",
    )
    args = parser.parse_args()
    if args.command == "setup":
        from .setup import setup

        try:
            result = setup(
                (
                    [c.strip() for c in args.clients.split(",") if c.strip()]
                    if args.clients is not None
                    else None
                ),
                args.data_dir,
                args.bin_dir,
                args.install_native,
                args.native_dir,
                args.archive,
                args.check,
            )
        except (ValueError, OSError, BackendError) as exc:
            print(json.dumps({"ready": False, "error": str(exc)}, indent=2))
            raise SystemExit(1)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["ready"] else 1)
    if args.command == "skill-path":
        from .setup import skill_path

        print(skill_path())
        return
    if args.command == "status":
        result = asyncio.run(mne_cpp_check_status())
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["ready"] else 1)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
