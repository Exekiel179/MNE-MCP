"""Exercise the configured stdio command without loading research data."""

import asyncio
import json

from mne_mcp.claude_config import build_psyclaw_entry, get_psyclaw_config_path


async def check_connection(entry: dict, timeout: float = 30) -> dict:
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    if entry.get("enabled") is False or entry.get("trusted") is False:
        raise ValueError(
            "The PsyClaw server is disabled or untrusted; review its configuration."
        )
    if entry.get("transport", "stdio") != "stdio":
        raise ValueError("Only stdio connections are supported by this check.")
    transport = StdioTransport(
        command=entry["command"],
        args=entry["args"],
        env=entry.get("env", {}),
        keep_alive=False,
    )
    async with asyncio.timeout(timeout):
        async with Client(transport, timeout=timeout, init_timeout=timeout) as client:
            tools = await client.list_tools()
            if "mne_check_status" not in {tool.name for tool in tools}:
                raise ValueError("Connected server does not expose mne_check_status.")
            result = await client.call_tool("mne_check_status", {})
            status = "\n".join(
                part.text for part in result.content if part.type == "text"
            )
            if result.is_error or "## MNE MCP Status" not in status:
                raise ValueError(
                    "mne_check_status did not return a valid status response."
                )
            return {
                "connected": True,
                "command": entry["command"],
                "tool_count": len(tools),
                "mne_available": "- MNE-Python: OK v" in status,
                "status": status,
            }


def verify_connection(*, registered: bool = False) -> dict:
    """Probe the exact interpreter, or the saved PsyClaw record on request."""
    entry = (
        json.loads(get_psyclaw_config_path().read_text(encoding="utf-8"))
        if registered
        else build_psyclaw_entry()
    )
    try:
        return asyncio.run(check_connection(entry))
    except Exception as error:
        raise ValueError(
            f"MCP connection failed ({type(error).__name__}: {error}). "
            "Check the registered Python path and its imports; no packages were installed."
        ) from error
