import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_live_stdio_session(tmp_path):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mne_cpp_mcp.server", "serve"],
        env={
            **os.environ,
            "PYTHONPATH": str(Path(__file__).parents[1] / "src"),
            "MNE_CPP_BIN_DIR": str(tmp_path),
            "MNE_CPP_DATA_DIR": str(tmp_path),
        },
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
            assert len(listing.tools) == 5
            status = await session.call_tool("mne_cpp_check_status", {})
            assert not status.isError
            assert status.structuredContent["ready"] is False
            invalid = await session.call_tool("mne_cpp_get_help", {"tool": "cmd.exe"})
            assert invalid.isError
            invalid = await session.call_tool(
                "mne_cpp_read_metadata", {"params": {"file": "relative.fif"}}
            )
            assert invalid.isError
