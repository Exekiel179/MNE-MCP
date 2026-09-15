import hashlib
import io
import json
import os
import stat
import subprocess
import sys
import urllib.error
import tomllib
import zipfile
from pathlib import Path

import pytest

from mne_cpp_mcp import setup as installer
from mne_cpp_mcp.backend import BackendError


@pytest.fixture
def home(tmp_path, monkeypatch):
    root = tmp_path / "home"
    root.mkdir()
    monkeypatch.setattr(Path, "home", lambda: root)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("MNE_CPP_BIN_DIR", raising=False)
    monkeypatch.setattr(installer.shutil, "which", lambda name: None)
    return root


@pytest.fixture
def native_ready(monkeypatch):
    async def ready(*args):
        return {"ready": True}

    monkeypatch.setattr(installer, "verify_native", ready)


@pytest.mark.parametrize("client", ["codex", "claude", "opencode"])
def test_setup_preserves_config_and_skill_and_is_idempotent(
    tmp_path, home, native_ready, client
):
    config, skills = installer.client_paths(client)
    config.parent.mkdir(parents=True, exist_ok=True)
    if client == "codex":
        old = '# keep comment\r\nmodel = "keep"\r\n[mcp_servers.other]\r\ncommand = "other"\r\n[mcp_servers."mne-cpp".env]\r\nOLD = "value"\r\n'
    else:
        key = "mcpServers" if client == "claude" else "mcp"
        old = json.dumps({"other": True, key: {"other": {"command": "keep"}}})
    config.write_bytes(old.encode())
    skill = skills / installer.SKILL_NAME / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("user modified skill")
    extra = skill.parent / "user-notes.md"
    extra.write_text("keep")
    result = installer.setup([client, client], tmp_path, bin_dir=tmp_path)
    assert result["ready"] and len(result["clients"]) == 1
    backup = Path(result["clients"][0]["config"]["backup"])
    assert backup.read_bytes() == old.encode()
    data = (
        tomllib.loads(config.read_text())
        if client == "codex"
        else json.loads(config.read_text())
    )
    servers = data[
        (
            "mcp_servers"
            if client == "codex"
            else "mcpServers" if client == "claude" else "mcp"
        )
    ]
    assert "other" in servers
    entry = servers["mne-cpp"]
    assert entry.get("env", entry.get("environment"))["MNE_CPP_DATA_DIR"] == str(
        tmp_path
    )
    assert "mne_cpp_mcp.server" in (
        entry["command"] if client == "opencode" else entry["args"]
    )
    if client == "codex":
        assert "# keep comment" in config.read_text()
        assert "OLD" not in entry["env"]
    assert extra.read_text() == "keep"
    assert (
        next(skill.parent.glob("SKILL.md.backup.*")).read_text()
        == "user modified skill"
    )
    second = installer.setup([client], tmp_path, bin_dir=tmp_path)
    assert second["clients"][0]["config"]["status"] == "unchanged"
    assert all(x["status"] == "unchanged" for x in second["clients"][0]["skills"])


def test_all_configs_validated_before_download(tmp_path, home, monkeypatch):
    config, _ = installer.client_paths("claude")
    config.write_text("{invalid")
    monkeypatch.setattr(
        installer, "install_native", lambda *a: pytest.fail("must not install")
    )
    with pytest.raises(ValueError):
        installer.setup(["codex", "claude"], tmp_path, install=True)
    assert not (home / ".codex").exists()


def test_check_missing_backend_is_read_only(tmp_path, home, monkeypatch):
    monkeypatch.setattr(
        installer, "_download", lambda *a: pytest.fail("must not download")
    )
    result = installer.setup(["codex"], tmp_path, install=True, check=True)
    assert result["check_only"] and not result["ready"]
    assert list(home.iterdir()) == []


def test_verification_failure_does_not_write_clients(tmp_path, home):
    with pytest.raises(BackendError):
        installer.setup(["codex"], tmp_path, bin_dir=tmp_path)
    assert list(home.iterdir()) == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"clients": []},
        {"clients": ["bad"]},
        {"clients": ["codex"], "archive": Path("x.zip")},
    ],
)
def test_invalid_setup_arguments(tmp_path, home, kwargs):
    with pytest.raises(ValueError):
        installer.setup(data_dir=tmp_path, bin_dir=tmp_path, **kwargs)
    assert list(home.iterdir()) == []


def test_environment_client_roots(tmp_path, home, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "custom-codex"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "custom-xdg"))
    config, skills = installer.client_paths("codex")
    assert config.parent == skills.parent == tmp_path / "custom-codex"
    assert (
        installer.client_paths("opencode")[0].parent
        == tmp_path / "custom-xdg" / "opencode"
    )


@pytest.mark.parametrize("client", ["codex", "claude", "opencode"])
def test_single_client_detected_from_config(home, client):
    config, _ = installer.client_paths(client)
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("")
    assert installer.select_clients(None) == [client]


def test_single_client_detected_from_executable(home, monkeypatch):
    monkeypatch.setattr(
        installer.shutil, "which", lambda name: "tool" if name == "claude" else None
    )
    assert installer.select_clients(None) == ["claude"]


def test_ambiguous_or_absent_clients_require_selection(home, monkeypatch):
    with pytest.raises(ValueError, match="detected: none"):
        installer.select_clients(None)
    monkeypatch.setattr(installer.shutil, "which", lambda name: "tool")
    with pytest.raises(ValueError, match="Add --clients"):
        installer.select_clients(None)
    assert installer.select_clients(["codex"]) == ["codex"]


def test_default_setup_installs_native_and_detects_client(
    tmp_path, home, native_ready, monkeypatch
):
    monkeypatch.setattr(
        installer.shutil, "which", lambda name: "tool" if name == "codex" else None
    )
    calls = []

    def install(destination, data_dir, archive):
        calls.append((destination, data_dir, archive))
        return destination / "bin"

    monkeypatch.setattr(installer, "install_native", install)
    result = installer.setup(None, tmp_path)
    assert result["ready"]
    assert calls == [(installer.default_native_dir(), tmp_path, None)]
    assert result["clients"][0]["client"] == "codex"


def test_default_setup_reuses_environment_without_installing(
    tmp_path, home, native_ready, monkeypatch
):
    monkeypatch.setenv("MNE_CPP_BIN_DIR", str(tmp_path))
    monkeypatch.setattr(
        installer, "install_native", lambda *a: pytest.fail("must reuse existing tools")
    )
    assert installer.setup(["codex"], tmp_path)["ready"]


def test_default_setup_does_not_replace_broken_environment(tmp_path, home, monkeypatch):
    monkeypatch.setenv("MNE_CPP_BIN_DIR", str(tmp_path / "missing"))
    monkeypatch.setattr(
        installer,
        "install_native",
        lambda *a: pytest.fail("must not reinstall on errors"),
    )
    with pytest.raises(ValueError, match="existing directory"):
        installer.setup(["codex"], tmp_path)
    assert list(home.iterdir()) == []


def test_default_check_does_not_install(tmp_path, home, monkeypatch):
    monkeypatch.setattr(
        installer, "install_native", lambda *a: pytest.fail("check must not install")
    )
    result = installer.setup(["codex"], tmp_path, check=True)
    assert result["check_only"] and not result["ready"]
    assert list(home.iterdir()) == []


def test_short_module_cli_accepts_minimal_setup(tmp_path):
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).parents[1] / "src"),
        "CODEX_HOME": str(tmp_path / "isolated-codex"),
        "MNE_CPP_BIN_DIR": str(tmp_path),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mne_cpp_mcp",
            "setup",
            "--data-dir",
            str(tmp_path),
            "--clients",
            "codex",
            "--check",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["check_only"] and not report["ready"]
    assert not (tmp_path / "isolated-codex").exists()


def make_archive(tmp_path, monkeypatch, member="bin/mne_show_fiff.exe"):
    path = tmp_path / "test.zip"
    with zipfile.ZipFile(path, "w") as bundle:
        item = zipfile.ZipInfo("fixture")
        item.filename = member
        bundle.writestr(item, b"fixture")
    monkeypatch.setattr(
        installer, "SHA256", hashlib.sha256(path.read_bytes()).hexdigest()
    )
    return path


def test_install_atomic_and_idempotent(tmp_path, monkeypatch, native_ready):
    monkeypatch.setattr(installer.platform, "system", lambda: "Windows")
    monkeypatch.setattr(installer.platform, "machine", lambda: "AMD64")
    archive = make_archive(tmp_path, monkeypatch)
    dest = tmp_path / "native"
    assert installer.install_native(dest, tmp_path, archive) == dest / "bin"
    monkeypatch.setattr(
        installer, "_extract", lambda *a: pytest.fail("must not re-extract")
    )
    assert installer.install_native(dest, tmp_path, archive) == dest / "bin"
    assert not list(tmp_path.glob(".mne-cpp-install-*"))


def test_failed_native_verification_leaves_no_install(tmp_path, monkeypatch):
    monkeypatch.setattr(installer.platform, "system", lambda: "Windows")
    monkeypatch.setattr(installer.platform, "machine", lambda: "AMD64")
    archive = make_archive(tmp_path, monkeypatch)

    async def fail(*args):
        raise BackendError("bad native version")

    monkeypatch.setattr(installer, "verify_native", fail)
    dest = tmp_path / "native"
    with pytest.raises(BackendError):
        installer.install_native(dest, tmp_path, archive)
    assert not dest.exists()
    assert not list(tmp_path.glob(".mne-cpp-install-*"))


def test_checksum_before_extraction(tmp_path):
    archive = tmp_path / "bad.zip"
    archive.write_bytes(b"not official")
    with pytest.raises(ValueError, match="SHA-256"):
        installer._extract(archive, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("member", ["../escape", "/escape", "C:/escape", "bin\\escape"])
def test_archive_paths_rejected(tmp_path, monkeypatch, member):
    archive = make_archive(tmp_path, monkeypatch, member)
    with pytest.raises(ValueError, match="Unsafe"):
        installer._extract(archive, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_archive_symlink_rejected(tmp_path, monkeypatch):
    archive = tmp_path / "link.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        item = zipfile.ZipInfo("bin/link")
        item.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(item, "../outside")
    monkeypatch.setattr(
        installer, "SHA256", hashlib.sha256(archive.read_bytes()).hexdigest()
    )
    with pytest.raises(ValueError, match="Unsafe"):
        installer._extract(archive, tmp_path / "out")


def test_config_changed_after_preflight(tmp_path):
    path = tmp_path / "config"
    path.write_text("new user change")
    with pytest.raises(ValueError, match="changed during"):
        installer.write_with_backup(path, b"installer", expected=b"old")
    assert path.read_text() == "new user change"


def test_download_uses_official_url_and_enforces_limit(tmp_path, monkeypatch):
    requests = []

    def response(request, timeout):
        requests.append((request.full_url, timeout))
        return io.BytesIO(b"download fixture")

    monkeypatch.setattr(installer.urllib.request, "urlopen", response)
    installer._download(tmp_path / "download.zip")
    assert (tmp_path / "download.zip").read_bytes() == b"download fixture"
    assert requests == [(installer.DOWNLOAD_URL, 30)]
    monkeypatch.setattr(installer, "MAX_DOWNLOAD", 4)
    with pytest.raises(ValueError, match="size limit"):
        installer._download(tmp_path / "oversize.zip")


def test_download_network_error_is_actionable(tmp_path, monkeypatch):
    def failed(*args, **kwargs):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(installer.urllib.request, "urlopen", failed)
    with pytest.raises(ValueError, match="--archive"):
        installer._download(tmp_path / "download.zip")


@pytest.mark.skipif(
    not os.getenv("MNE_CPP_TEST_DOWNLOAD"), reason="Opt in to official network download"
)
def test_official_download_digest(tmp_path):
    archive = tmp_path / installer.ASSET
    installer._download(archive)
    with archive.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == installer.SHA256


def test_cli_setup_json_failure(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mne_cpp_mcp.server",
            "setup",
            "--clients",
            "unknown",
            "--bin-dir",
            str(tmp_path),
            "--data-dir",
            str(tmp_path),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["ready"] is False


@pytest.mark.skipif(
    not os.getenv("MNE_CPP_TEST_ARCHIVE"), reason="Set official Windows archive path"
)
def test_offline_official_install_and_registered_stdio(tmp_path, home):
    import asyncio
    import mne
    import numpy as np
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    archive = Path(os.environ["MNE_CPP_TEST_ARCHIVE"])
    destination = tmp_path / "official-runtime"
    installed = installer.setup(
        ["codex", "claude", "opencode"],
        tmp_path,
        install=True,
        native_dir=destination,
        archive=archive,
    )
    assert installed["ready"]
    again = installer.setup(
        ["codex"], tmp_path, install=True, native_dir=destination, archive=archive
    )
    assert again["clients"][0]["config"]["status"] == "unchanged"
    config, _ = installer.client_paths("codex")
    entry = tomllib.loads(config.read_text())["mcp_servers"]["mne-cpp"]
    assert entry["env"]["MNE_CPP_BIN_DIR"] == str(destination / "bin")
    data = tmp_path / "native-test_raw.fif"
    mne.io.RawArray(np.zeros((1, 200)), mne.create_info(["Cz"], 200, "eeg")).save(data)

    async def verify():
        params = StdioServerParameters(
            command=entry["command"],
            args=entry["args"],
            env={
                **os.environ,
                **entry["env"],
                "PYTHONPATH": str(Path(__file__).parents[1] / "src"),
            },
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                status = await session.call_tool("mne_cpp_check_status", {})
                assert status.structuredContent["ready"]
                result = await session.call_tool(
                    "mne_cpp_read_metadata", {"params": {"file": str(data)}}
                )
                assert not result.isError
                assert result.structuredContent["sfreq_hz"] == 200

    asyncio.run(verify())
