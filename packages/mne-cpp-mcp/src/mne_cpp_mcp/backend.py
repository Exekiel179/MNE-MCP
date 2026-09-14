"""Restricted, cancellable inspection using official MNE-CPP 2.3 CLI tools."""

import asyncio
import hashlib
import os
import re
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ToolName = Literal["mne_show_fiff", "mne_evoked_data_summary"]
TOOLS = ("mne_show_fiff", "mne_evoked_data_summary")
BLOCKED = {
    "filter_raw": "2.3.0 mne_process_raw accepted filters but saved unchanged samples in the verified fixture.",
    "find_events": "2.3.0 mne_process_raw did not export known synthetic trigger events in the verified fixture.",
}


class FileParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    file: str = Field(description="Absolute path to an existing uncompressed .fif file")


class InspectParameters(FileParameters):
    blocks_only: bool = Field(
        default=True, description="List blocks without personal metadata"
    )


class BackendError(RuntimeError):
    """Actionable native backend failure."""


class Backend:
    def __init__(self, bin_dir: Path, data_dir: Path, timeout: float = 120):
        self.bin_dir = bin_dir.resolve()
        self.data_dir = data_dir.resolve()
        self.timeout = timeout
        self.lock = asyncio.Lock()

    @classmethod
    def from_environment(cls):
        required = ["MNE_CPP_BIN_DIR", "MNE_CPP_DATA_DIR"]
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            raise BackendError("Set absolute paths for " + ", ".join(missing))
        paths = [Path(os.environ[name]).expanduser() for name in required]
        if not all(path.is_absolute() and path.is_dir() for path in paths):
            raise BackendError("MNE_CPP paths must be absolute existing directories")
        return cls(*paths)

    def executable(self, tool: ToolName) -> Path:
        if tool not in TOOLS:
            raise BackendError(
                "Unsupported executable; use a registered inspection tool"
            )
        exe = (self.bin_dir / (tool + (".exe" if os.name == "nt" else ""))).resolve()
        if not exe.is_relative_to(self.bin_dir) or not exe.is_file():
            raise BackendError(
                f"Missing {tool} in MNE_CPP_BIN_DIR. Install official native tools including Qt dependencies."
            )
        return exe

    def input_file(self, name: str) -> Path:
        path = Path(name)
        if not path.is_absolute():
            raise BackendError("Input must be an absolute path")
        path = path.resolve()
        if not path.is_relative_to(self.data_dir):
            raise BackendError("Input is outside MNE_CPP_DATA_DIR")
        if path.suffix.lower() != ".fif" or not path.is_file():
            raise BackendError("Input must be an existing uncompressed .fif file")
        # Validate only the mandatory FIFF file-id header, not an ad hoc FIFF reader.
        with path.open("rb") as stream:
            if stream.read(12) != bytes.fromhex("000000640000001f00000014"):
                raise BackendError("Input has no valid FIFF file-id header")
        return path

    async def run(
        self, tool: ToolName, args: list[str], help_call: bool = False
    ) -> dict:
        exe = self.executable(tool)
        command = [str(exe), *args]
        started = time.perf_counter()
        env = os.environ.copy()
        env["PATH"] = str(self.bin_dir) + os.pathsep + env.get("PATH", "")
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
                cwd=self.bin_dir,
                env=env,
                **({"creationflags": 0x08000000} if os.name == "nt" else {}),
            )
        except OSError as exc:
            raise BackendError(
                "Cannot start native executable. Check permissions, platform and Qt runtime dependencies."
            ) from exc

        async def drain(stream):
            kept = bytearray()
            total = 0
            while chunk := await stream.read(8192):
                total += len(chunk)
                kept.extend(chunk[: max(0, 65536 - len(kept))])
            return kept.decode("utf-8", errors="replace"), total > len(kept)

        readers = [
            asyncio.create_task(drain(process.stdout)),
            asyncio.create_task(drain(process.stderr)),
        ]
        try:
            await asyncio.wait_for(process.wait(), timeout=self.timeout)
            stdout, stderr = await asyncio.gather(*readers)
        except (TimeoutError, asyncio.CancelledError) as exc:
            if process.returncode is None:
                process.kill()
            await process.wait()
            await asyncio.gather(*readers)
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise BackendError(
                "Native operation timed out and was terminated; no result is verified."
            ) from exc
        result = {
            "command": command,
            "exit_code": process.returncode,
            "stdout": stdout[0],
            "stderr": stderr[0],
            "truncated": stdout[1] or stderr[1],
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "backend": "MNE-CPP",
            "executable_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
        }
        # The upstream FIFF help command intentionally returns 1.
        if process.returncode != 0 and not (
            help_call and tool == "mne_show_fiff" and process.returncode == 1
        ):
            raise BackendError(
                f"{tool} failed (exit {process.returncode}): {stderr[0][-2000:]} {stdout[0][-2000:]}"
            )
        return result

    async def status(self) -> dict:
        status = {
            "backend": "MNE-CPP",
            "tested_api": "2.3.0",
            "tools": {},
            "ready": False,
            "scope": "read-only inspection preview; not a full analysis backend",
            "blocked_capabilities": BLOCKED,
        }
        for tool in TOOLS:
            try:
                result = await self.run(tool, ["--version"])
                version = result["stdout"] + result["stderr"]
                compatible = bool(re.search(r"\b2\.3\.0\b", version))
                status["tools"][tool] = {
                    "available": True,
                    "compatible": compatible,
                    "version_output": version.strip(),
                }
            except BackendError as exc:
                status["tools"][tool] = {"available": False, "error": str(exc)}
        status["ready"] = all(x.get("compatible") for x in status["tools"].values())
        return status

    async def require_version(self):
        status = await self.status()
        if not status["ready"]:
            raise BackendError(
                f"The bridge requires verified MNE-CPP 2.3.0 tools: {status['tools']}"
            )

    async def inspect(self, params: InspectParameters) -> dict:
        async with self.lock:
            await self.require_version()
            path = self.input_file(params.file)
            args = ["--in", str(path)] + (["--blocks"] if params.blocks_only else [])
            result = await self.run("mne_show_fiff", args)
            if not result["stdout"].strip():
                raise BackendError("Native FIFF inspection returned no content")
            return result

    async def metadata(self, params: FileParameters) -> dict:
        async with self.lock:
            await self.require_version()
            path = self.input_file(params.file)
            result = await self.run(
                "mne_show_fiff", ["--in", str(path), "--tag", "201", "--verbose"]
            )
            matches = re.findall(
                r"^\s*201\s*=\s*sfreq\s+([0-9.eE+-]+)\s*$",
                result["stdout"],
                re.MULTILINE,
            )
            if len(matches) != 1 or not 0 < float(matches[0]) < 1e9:
                raise BackendError(
                    "Cannot verify one sampling frequency from native FIFF output"
                )
            sfreq = float(matches[0])
            result.update(
                {
                    "file": str(path),
                    "sfreq_hz": sfreq,
                    "nyquist_hz": sfreq / 2,
                    "interpretation": "Sampling metadata only; no signal-quality or biological inference.",
                }
            )
            return result

    async def evoked_summary(self, params: FileParameters) -> dict:
        async with self.lock:
            await self.require_version()
            path = self.input_file(params.file)
            result = await self.run("mne_evoked_data_summary", ["--meas", str(path)])
            if not re.search(
                r"Number of evoked data sets:\s*[1-9][0-9]*", result["stdout"]
            ):
                raise BackendError("No evoked datasets were verified in native output")
            result["interpretation"] = (
                "Descriptive evoked metadata only; nave is an averaging count, not an independent participant count."
            )
            return result
