"""Explicit native installation and selected-client setup; never runs at startup."""

import asyncio
import hashlib
import json
import os
import platform
import shutil
import stat
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import MutableMapping
from datetime import datetime
from pathlib import Path, PurePosixPath

import tomlkit

from .backend import Backend, BackendError

ASSET = "mne-cpp-2.3.0-windows-dynamic-x86_64.zip"
DOWNLOAD_URL = f"https://github.com/mne-tools/mne-cpp/releases/download/v2.3.0/{ASSET}"
# Verified against the official GitHub release asset digest, not a user-supplied hash.
SHA256 = "98becc6bdc095f2a682836f64bb25fa7963e70a7244331ae9daf73025478d5c0"
MAX_DOWNLOAD = 64 * 1024 * 1024
MAX_EXTRACTED = 256 * 1024 * 1024
SKILL_NAME = "mne-cpp-analyst"


def skill_path() -> Path:
    bundled = Path(__file__).parent / "_bundled" / "skills" / SKILL_NAME
    source = Path(__file__).parents[2] / "skills" / SKILL_NAME
    path = bundled if bundled.is_dir() else source
    if not (path / "SKILL.md").is_file():
        raise ValueError("Companion skill missing; reinstall this package")
    return path


def default_native_dir() -> Path:
    return Path.home() / ".mne-cpp-mcp" / "native" / "2.3.0"


def existing_directory(path: Path, label: str) -> Path:
    path = path.expanduser()
    if not path.is_absolute() or not path.is_dir():
        raise ValueError(f"{label} must be an absolute existing directory")
    return path.resolve()


def _download(destination: Path) -> None:
    request = urllib.request.Request(
        DOWNLOAD_URL, headers={"User-Agent": "mne-cpp-mcp"}
    )
    try:
        with (
            urllib.request.urlopen(request, timeout=30) as response,
            destination.open("xb") as out,
        ):
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_DOWNLOAD:
                    raise ValueError("Native download exceeds the verified size limit")
                out.write(chunk)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ValueError(
            "Official download failed. Check network access, or use --archive with the official ZIP. "
            "No client configuration was written."
        ) from exc


def _extract(archive: Path, destination: Path) -> None:
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != SHA256:
            raise ValueError(
                "Native archive SHA-256 mismatch; refusing to extract or run it"
            )
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if (
            len(entries) > 10000
            or sum(item.file_size for item in entries) > MAX_EXTRACTED
        ):
            raise ValueError("Native archive exceeds extraction limits")
        for item in entries:
            path = PurePosixPath(item.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in item.orig_filename
                or ":" in item.filename
                or stat.S_ISLNK(item.external_attr >> 16)
            ):
                raise ValueError("Unsafe path in native archive")
        bundle.extractall(destination)


async def verify_native(bin_dir: Path, data_dir: Path) -> dict:
    result = await Backend(bin_dir, data_dir, timeout=15).status()
    if not result["ready"]:
        raise BackendError(
            f"Native verification failed; client configuration unchanged: {result['tools']}"
        )
    return result


def install_native(
    destination: Path, data_dir: Path, archive: Path | None = None
) -> Path:
    if platform.system() != "Windows" or platform.machine().lower() not in {
        "amd64",
        "x86_64",
    }:
        raise ValueError(
            "Automatic native installation supports Windows x86_64 only; use --bin-dir for a user-managed native build"
        )
    destination = destination.expanduser()
    if not destination.is_absolute() or destination.is_symlink():
        raise ValueError("Native destination must be an absolute, non-symlink path")
    destination = destination.resolve()
    if destination.exists():
        marker = destination / "mne-cpp-mcp-install.json"
        manifest = (
            json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else None
        )
        if not isinstance(manifest, dict) or manifest.get("archive_sha256") != SHA256:
            raise ValueError(
                "Native destination already exists and is not managed by this installer; use --bin-dir or a new --native-dir"
            )
        asyncio.run(verify_native(destination / "bin", data_dir))
        return destination / "bin"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".mne-cpp-install-", dir=destination.parent
    ) as temporary:
        stage = Path(temporary)
        if archive is None:
            archive = stage / ASSET
            _download(archive)
        extracted = stage / "runtime"
        _extract(archive, extracted)
        asyncio.run(verify_native(extracted / "bin", data_dir))
        (extracted / "mne-cpp-mcp-install.json").write_text(
            json.dumps({"archive_sha256": SHA256, "source": DOWNLOAD_URL}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        if destination.exists():
            raise ValueError(
                "Native destination appeared during installation; refusing to overwrite it"
            )
        extracted.rename(destination)
    return destination / "bin"


def client_paths(client: str) -> tuple[Path, Path]:
    home = Path.home()
    if client == "codex":
        root = Path(os.environ.get("CODEX_HOME", str(home / ".codex")))
        return root / "config.toml", root / "skills"
    if client == "claude":
        return home / ".claude.json", home / ".claude" / "skills"
    if client == "opencode":
        root = (
            Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))) / "opencode"
        )
        return root / "opencode.json", root / "skills"
    raise ValueError(f"Unknown client: {client}; choose claude, codex, opencode")


def select_clients(clients: list[str] | None) -> list[str]:
    if clients is not None:
        if not clients:
            raise ValueError("Select at least one client with --clients")
        return list(dict.fromkeys(clients))
    detected = [
        client
        for client in ("codex", "claude", "opencode")
        if client_paths(client)[0].is_file() or shutil.which(client)
    ]
    if len(detected) != 1:
        raise ValueError(
            f"Cannot select one client automatically (detected: {', '.join(detected) or 'none'}). "
            "Add --clients codex, --clients claude, or --clients opencode."
        )
    return detected


def config_content(
    client: str, path: Path, bin_dir: Path, data_dir: Path
) -> tuple[str, str]:
    original = path.read_bytes().decode("utf-8") if path.exists() else ""
    env = {"MNE_CPP_BIN_DIR": str(bin_dir), "MNE_CPP_DATA_DIR": str(data_dir)}
    command = str(Path(sys.executable).absolute())
    args = ["-m", "mne_cpp_mcp.server", "serve"]
    if client == "codex":
        data = tomlkit.parse(original)
        entry = {"command": command, "args": args, "env": env, "enabled": True}
        key = "mcp_servers"
    else:
        data = json.loads(original) if original.strip() else {}
        key = "mcpServers" if client == "claude" else "mcp"
        entry = {"type": "stdio", "command": command, "args": args, "env": env}
        if client == "opencode":
            entry = {
                "type": "local",
                "command": [command, *args],
                "environment": env,
                "enabled": True,
            }
    if not isinstance(data, MutableMapping):
        raise ValueError(f"Expected a configuration object in {path}")
    servers = data.setdefault(key, {})
    if not isinstance(servers, MutableMapping):
        raise ValueError(f"Expected a {key} table in {path}")
    if servers.get("mne-cpp") == entry:
        return original, original
    servers["mne-cpp"] = entry
    updated = (
        tomlkit.dumps(data)
        if client == "codex"
        else json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    )
    return original, updated


def write_with_backup(
    path: Path, content: bytes, expected: bytes | None = None
) -> dict:
    if path.is_symlink():
        raise ValueError(f"Refusing to replace symlink: {path}")
    old = path.read_bytes() if path.exists() else None
    if expected is not None and (old or b"") != expected:
        raise ValueError(f"Configuration changed during setup; retry: {path}")
    if old == content:
        return {"path": str(path), "status": "unchanged", "backup": None}
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if old is not None:
        backup = path.with_name(
            path.name + ".backup." + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        )
        shutil.copy2(path, backup)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=".mne-cpp-", delete=False
    ) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "path": str(path),
        "status": "updated" if old is not None else "created",
        "backup": str(backup) if backup else None,
    }


def setup(
    clients: list[str] | None,
    data_dir: Path,
    bin_dir: Path | None = None,
    install: bool | None = None,
    native_dir: Path | None = None,
    archive: Path | None = None,
    check: bool = False,
) -> dict:
    clients = select_clients(clients)
    if install is None:
        if bin_dir is None and archive is None and native_dir is None:
            configured = os.environ.get("MNE_CPP_BIN_DIR")
            if configured:
                bin_dir = Path(configured)
        install = bin_dir is None
    if bin_dir is not None and install:
        raise ValueError("Choose either --bin-dir or --install-native")
    if (archive is not None or native_dir is not None) and not install:
        raise ValueError("--archive and --native-dir require --install-native")
    data_dir = existing_directory(data_dir, "--data-dir")
    native_dir = native_dir or default_native_dir()
    if bin_dir is not None:
        bin_dir = existing_directory(bin_dir, "--bin-dir")
    elif install:
        if not native_dir.expanduser().is_absolute():
            raise ValueError("--native-dir must be absolute")
        bin_dir = native_dir.expanduser().resolve() / "bin"
    else:
        raise ValueError("Select --bin-dir for existing tools or --install-native")
    source = skill_path()
    # Parse every selected config before downloading or mutating anything.
    plans = []
    for client in clients:
        config, skills = client_paths(client)
        original, updated = config_content(client, config, bin_dir, data_dir)
        plans.append((client, config, skills, original, updated))
    if check:
        status = asyncio.run(Backend(bin_dir, data_dir, timeout=15).status())
        return {
            "check_only": True,
            "ready": status["ready"],
            "native": status,
            "clients": [
                {"client": c, "config": str(p), "skill": str(s / SKILL_NAME)}
                for c, p, s, _, _ in plans
            ],
        }
    if install:
        bin_dir = install_native(native_dir, data_dir, archive)
    status = asyncio.run(verify_native(bin_dir, data_dir))
    results = []
    for client, config, skills, original, updated in plans:
        installed = []
        for item in sorted(source.rglob("*")):
            if item.is_file():
                installed.append(
                    write_with_backup(
                        skills / SKILL_NAME / item.relative_to(source),
                        item.read_bytes(),
                    )
                )
        result = write_with_backup(
            config, updated.encode("utf-8"), expected=original.encode("utf-8")
        )
        results.append({"client": client, "config": result, "skills": installed})
    return {
        "ready": True,
        "native": status,
        "bin_dir": str(bin_dir),
        "clients": results,
        "next_step": "Restart selected clients and call mne_cpp_check_status; ready covers inspection only.",
    }
