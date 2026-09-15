import asyncio
import os
import sys
from pathlib import Path

import pytest
from mne_cpp_mcp.backend import Backend, BackendError, FileParameters, InspectParameters
from pydantic import ValidationError


def test_paths_and_allowlist(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    valid = data / "recording with spaces.fif"
    valid.write_bytes(bytes.fromhex("000000640000001f00000014"))
    outside = tmp_path / "outside.fif"
    outside.write_bytes(b"fixture")
    backend = Backend(tmp_path, data)
    assert backend.input_file(str(valid)) == valid
    for name in [
        "relative.fif",
        str(outside),
        str(data / "missing.fif"),
        str(data / "../outside.fif"),
    ]:
        with pytest.raises(BackendError):
            backend.input_file(name)
    with pytest.raises(BackendError, match="Unsupported"):
        backend.executable("mne_process_raw")
    with pytest.raises(BackendError, match="Missing"):
        backend.executable("mne_show_fiff")


def test_schema_rejects_extra_and_wrong_types():
    with pytest.raises(ValidationError):
        InspectParameters(file="x.fif", blocks_only="false")
    with pytest.raises(ValidationError):
        FileParameters(file="x.fif", args=["--save"])


def test_missing_environment(monkeypatch):
    monkeypatch.delenv("MNE_CPP_BIN_DIR", raising=False)
    with pytest.raises(BackendError, match="MNE_CPP_BIN_DIR"):
        Backend.from_environment()


@pytest.mark.asyncio
async def test_missing_status(tmp_path):
    result = await Backend(tmp_path, tmp_path).status()
    assert result["ready"] is False
    assert "filter_raw" in result["blocked_capabilities"]


@pytest.mark.asyncio
async def test_real_subprocess_bounded_output_and_nonzero(tmp_path, monkeypatch):
    backend = Backend(tmp_path, tmp_path)
    monkeypatch.setattr(backend, "executable", lambda tool: Path(sys.executable))
    result = await backend.run("mne_show_fiff", ["-c", "print('x'*100000)"])
    assert result["truncated"] and len(result["stdout"]) == 65536
    assert len(result["executable_sha256"]) == 64
    with pytest.raises(BackendError, match="exit 3"):
        await backend.run("mne_show_fiff", ["-c", "import sys; sys.exit(3)"])
    result = await backend.run(
        "mne_show_fiff", ["-c", "import sys; sys.exit(1)"], help_call=True
    )
    assert result["exit_code"] == 1


@pytest.mark.asyncio
async def test_timeout_and_cancellation_kill_native(tmp_path, monkeypatch):
    backend = Backend(tmp_path, tmp_path, timeout=0.1)
    monkeypatch.setattr(backend, "executable", lambda tool: Path(sys.executable))
    original = asyncio.create_subprocess_exec
    processes = []

    async def spawn(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(BackendError, match="timed out"):
        await backend.run("mne_show_fiff", ["-c", "import time; time.sleep(30)"])
    assert processes[-1].returncode is not None
    backend.timeout = 30
    task = asyncio.create_task(
        backend.run("mne_show_fiff", ["-c", "import time; time.sleep(30)"])
    )
    while len(processes) < 2:
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert processes[-1].returncode is not None


@pytest.mark.asyncio
async def test_metadata_fails_closed(tmp_path, monkeypatch):
    backend = Backend(tmp_path, tmp_path)
    path = tmp_path / "raw.fif"
    path.write_bytes(bytes.fromhex("000000640000001f00000014"))

    async def version():
        pass

    async def run(*args):
        return {"stdout": "201 = sfreq not-a-number"}

    monkeypatch.setattr(backend, "require_version", version)
    monkeypatch.setattr(backend, "run", run)
    with pytest.raises(BackendError, match="sampling frequency"):
        await backend.metadata(FileParameters(file=str(path)))


@pytest.mark.asyncio
async def test_version_probe_cache_refresh_and_invalidation(tmp_path, monkeypatch):
    backend = Backend(tmp_path, tmp_path)
    key = ["first"]
    calls = []
    monkeypatch.setattr(backend, "fingerprint", lambda tool: (tool, key[0]))

    async def run(tool, args):
        calls.append(tool)
        return {"stdout": "MNE-CPP 2.3.0", "stderr": "", "truncated": False}

    monkeypatch.setattr(backend, "run", run)
    await backend.require_version()
    await backend.require_version()
    assert len(calls) == 2
    result = await backend.status()
    assert len(calls) == 4
    result["ready"] = False
    await backend.require_version()
    assert len(calls) == 4
    key[0] = "changed"
    await backend.require_version()
    assert len(calls) == 6
    monkeypatch.setattr("mne_cpp_mcp.backend.time.monotonic", lambda: float("inf"))
    await backend.require_version()
    assert len(calls) == 8


@pytest.mark.asyncio
async def test_invalid_path_never_launches_native(tmp_path, monkeypatch):
    backend = Backend(tmp_path, tmp_path)

    async def unexpected():
        pytest.fail("invalid paths should fail before native probes")

    monkeypatch.setattr(backend, "require_version", unexpected)
    for operation in (backend.metadata, backend.evoked_summary, backend.inspect):
        with pytest.raises(BackendError, match="absolute"):
            await operation(InspectParameters(file="relative.fif"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation, output",
    [
        ("metadata", "201 = sfreq 200"),
        ("evoked_summary", "Number of evoked data sets: 1"),
    ],
)
async def test_truncated_output_cannot_support_interpretation(
    tmp_path, monkeypatch, operation, output
):
    backend = Backend(tmp_path, tmp_path)
    path = tmp_path / "recording.fif"
    path.write_bytes(bytes.fromhex("000000640000001f00000014"))

    async def version():
        pass

    async def run(*args):
        return {"stdout": output, "truncated": True}

    monkeypatch.setattr(backend, "require_version", version)
    monkeypatch.setattr(backend, "run", run)
    with pytest.raises(BackendError, match="truncated"):
        await getattr(backend, operation)(FileParameters(file=str(path)))


@pytest.mark.asyncio
async def test_mcp_schema_and_validation(monkeypatch):
    from mcp.server.fastmcp.exceptions import ToolError
    from mne_cpp_mcp import server

    tools = await server.mcp.list_tools()
    names = {tool.name for tool in tools}
    assert len(names) == 5
    assert "mne_cpp_filter_raw" not in names
    assert all(tool.annotations.readOnlyHint for tool in tools)
    with pytest.raises(ToolError):
        await server.mcp.call_tool("mne_cpp_get_help", {"tool": "cmd.exe"})


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("MNE_CPP_TEST_BIN_DIR"), reason="Set native test backend path"
)
async def test_native_fiff_workflow(tmp_path, monkeypatch):
    import mne
    import numpy as np

    monkeypatch.setenv("_MNE_FAKE_HOME_DIR", str(tmp_path))
    backend = Backend(Path(os.environ["MNE_CPP_TEST_BIN_DIR"]), tmp_path)
    info = mne.create_info(["Cz", "Pz"], 200, "eeg")
    raw = mne.io.RawArray(np.zeros((2, 2000)), info)
    path = tmp_path / "synthetic_raw.fif"
    raw.save(path)
    result = await backend.status()
    assert result["ready"], result
    result = await backend.inspect(InspectParameters(file=str(path)))
    assert result["exit_code"] == 0 and result["stdout"].strip()
    metadata = await backend.metadata(FileParameters(file=str(path)))
    assert metadata["sfreq_hz"] == 200 and metadata["nyquist_hz"] == 100
    evoked = mne.EvokedArray(
        np.zeros((2, 101)), info, tmin=-0.1, nave=12, comment="synthetic-condition"
    )
    ave = tmp_path / "synthetic-ave.fif"
    evoked.save(ave)
    summary = await backend.evoked_summary(FileParameters(file=str(ave)))
    assert summary["dataset_count"] == 1
    assert "synthetic-condition" in summary["stdout"]
    assert "Nave       : 12" in summary["stdout"]
    assert "Channels   : 2" in summary["stdout"]
    assert "-0.100 to 0.400" in summary["stdout"]
    with pytest.raises(BackendError):
        await backend.evoked_summary(FileParameters(file=str(path)))
