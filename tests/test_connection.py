"""Real stdio verification, isolated from the user's MNE preferences."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from mne_mcp import claude_config as cc
from mne_mcp.connection import check_connection, verify_connection


@pytest.fixture
def isolated_psyclaw(tmp_path, monkeypatch):
    for key, value in {
        "MNE_MCP_PSYCLAW_CONFIG": tmp_path / ".psyclaw/mcp/mne.json",
        "MNE_MCP_CONFIG": tmp_path / "defaults.json",
        "MNE_MCP_RESULTS_DIR": tmp_path / "results",
        "MNE_MCP_DATA_DIR": tmp_path,
        "MPLCONFIGDIR": tmp_path / "matplotlib",
        "_MNE_FAKE_HOME_DIR": tmp_path,
        "MNE_DONTWRITE_HOME": "true",
        "MPLBACKEND": "Agg",
    }.items():
        monkeypatch.setenv(key, str(value))
    cc.configure_clients(["psyclaw"])
    return tmp_path


def test_saved_psyclaw_stdio_status(isolated_psyclaw):
    result = verify_connection(registered=True)
    assert result["connected"]
    assert result["mne_available"]
    assert result["tool_count"] >= 41
    assert "Session execution: idle" in result["status"]


@pytest.mark.parametrize("field", ["enabled", "trusted"])
async def test_disabled_connection_rejected(field):
    with pytest.raises(ValueError, match="disabled or untrusted"):
        await check_connection({field: False})


async def test_missing_executable_fails():
    with pytest.raises(Exception):
        await check_connection(
            {"command": "mne-mcp-nonexistent-executable", "args": []}, timeout=2
        )


async def test_hung_server_times_out():
    import sys

    with pytest.raises((TimeoutError, ExceptionGroup)):
        await check_connection(
            {"command": sys.executable, "args": ["-c", "import time; time.sleep(60)"]},
            timeout=1,
        )


def test_psyclaw_runtime_synthetic_workflow(isolated_psyclaw):
    """Opt-in contract test against an actual PsyClaw checkout/build."""
    checkout = os.environ.get("PSYCLAW_TEST_CHECKOUT")
    if not checkout:
        pytest.skip("Set PSYCLAW_TEST_CHECKOUT to run PsyClaw's real runtime")
    runtime = Path(checkout) / "dist/src/integrations/mcp-runtime.js"
    skills = Path(checkout) / "dist/src/skills/user-skills.js"
    result = subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("psyclaw_smoke.mjs")),
            str(isolated_psyclaw),
            runtime.as_uri(),
            skills.as_uri(),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["connected"]
    assert report["skills"] == 14
    assert report["synthetic_analysis"]
