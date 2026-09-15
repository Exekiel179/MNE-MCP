# mne-cpp-mcp

Version 0.1.0a1: **read-only native inspection preview**, not a replacement for
MNE-Python MCP. Python handles MCP transport; official MNE-CPP executables read
the data. MNE-Python is not a runtime dependency and no algorithm silently falls
back to Python.

## Scope

Five MCP tools: `mne_cpp_check_status`, `mne_cpp_get_help`,
`mne_cpp_inspect_fiff`, `mne_cpp_read_metadata`, `mne_cpp_evoked_summary`.
Only uncompressed FIFF files under an explicitly configured data directory are
accessible. Native output is bounded at 64 KiB per stream, and truncated output
is marked. Calls time out after 120 seconds and terminate the native process.

**Blocked:** filtering, trigger extraction, ICA, epoching, connectivity, decoding,
source reconstruction and real-time acquisition are not implemented by this MCP.
This is a limitation of our current bridge, not a claim that the MNE-CPP library
cannot perform scientific analysis. Evoked summary reads an already-averaged file;
it does not compute epochs or averages from raw recordings. A complete native
workflow requires a compiled adapter to the appropriate MNE-CPP library APIs
(or repaired, verified upstream CLI paths), plus signal-level tests for each
operation. Installing the runtime or improving a skill does not implement that
missing analysis layer. MNE-Python MCP remains the implemented analysis backend.
Testing found that the official 2.3.0 `mne_process_raw` saved unchanged samples
despite filter arguments, and did not export known trigger events. These commands
are deliberately not exposed. See [validation evidence](VALIDATION.md).

There is no general speedup claim here. Equivalent algorithms, thread counts,
numerical tolerances, I/O and process-start overhead must be benchmarked first.

## Install

Download the wheel and source package from the
[C++ preview release](https://github.com/Exekiel179/MNE-MCP/releases/tag/mne-cpp-v0.1.0a1).
Install the downloaded wheel with `python -m pip install <wheel-path>`, then run
the setup command below. This GitHub preview is separate from the Python backend
release and is not published to PyPI.

Use Python 3.12+ in a dedicated environment. MNE-Python is not required.
The verified native platform is Windows x86_64; macOS/Linux remain untested.

From the MNE-MCP checkout:

```text
python -m pip install ./packages/mne-cpp-mcp
mne-cpp-mcp setup --data-dir "D:/research/data"
```

Replace the data directory with an existing absolute directory you authorize the
MCP to read. This is the only required option: it defines the file-access boundary.
Setup detects a client from its configuration file or executable on PATH. If
exactly one is detected, it is selected. Otherwise add `--clients codex`,
`--clients claude` (Claude Code), or `--clients opencode`; it never configures all
clients automatically. Setup installs the companion skill for each selected client.
Restart those clients and call `mne_cpp_check_status`.

If the console command is not on PATH, use the same environment's interpreter:
`python -m mne_cpp_mcp setup --data-dir "D:/research/data"`.
The older `python -m mne_cpp_mcp.server` entrypoint remains supported.

This package is not published to PyPI. The pip command installs only the light
bridge. Setup reuses `--bin-dir` or `MNE_CPP_BIN_DIR` when provided; otherwise it
reuses the managed runtime or installs it if missing. It downloads the official Windows
dynamic ZIP including Qt, checks a release SHA-256 pinned by the bridge, extracts
to `~/.mne-cpp-mcp/native/2.3.0`, and verifies both native executables before
registering the server. No administrator or global PATH changes are needed.
The native API is fixed to the verified 2.3.0 release internally; users need not
choose or type a package version. No analysis call installs anything.

Already have native tools? Add
`--bin-dir "C:/tools/mne-cpp/bin"`. For offline installation, add
`--archive "C:/Downloads/mne-cpp-2.3.0-windows-dynamic-x86_64.zip"`;
it must match the same official archive checksum.
Use `--native-dir` with an absolute new directory to change the native destination.
The old `--install-native` flag remains accepted to explicitly select the managed
runtime. Broken configured runtimes cause an error, not automatic reinstallation.

Add `--check` to the setup command for a read-only preflight: no downloads,
extraction, configuration or skill writes. Exit code 1 means not ready; inspect
the JSON error/status rather than repeatedly reinstalling. Setup itself also
returns JSON. It backs up changed config/skill files, retains unrelated entries
and extra skill files, and leaves unchanged files untouched on repeat runs.
All selected configs are parsed before installation, but writes across multiple
clients are not one transaction; on a filesystem error, inspect backups and rerun.

See [agent installation instructions](INSTALL_AGENT.md) for a natural-language
installation request and acceptance checks.

For clients outside the three setup targets, configure manually:

Configure your MCP client with the absolute environment interpreter:

```json
{
  "mcpServers": {
    "mne-cpp": {
      "command": "C:/path/to/venv/Scripts/python.exe",
      "args": ["-m", "mne_cpp_mcp.server", "serve"],
      "env": {
        "MNE_CPP_BIN_DIR": "C:/path/to/mne-cpp/bin",
        "MNE_CPP_DATA_DIR": "D:/research/data"
      }
    }
  }
}
```

Use the same command, args and env in the client's native format (Codex uses
TOML). Restart the client and require `mne_cpp_check_status.ready == true`.
For a terminal check, set the environment variables and run
`python -m mne_cpp_mcp.server status`. Missing/incompatible executables are
reported without downloading or installing anything.

The wheel bundles `mne-cpp-analyst`; setup installs it automatically. For other clients run
`python -m mne_cpp_mcp.server skill-path` to find the directory to install in your
client's skills directory. Back up an existing copy before replacing it.

## Examples

- Check status, then inspect the block structure of `sub-01_raw.fif`.
- Read sampling metadata before planning a subsequent MNE-Python filter workflow.
- Summarize an `-ave.fif` file; do not interpret nave as participant count.

Detailed metadata can contain participant information. Default inspection shows
blocks only. Nothing is uploaded by this bridge, but MCP output becomes visible
to the selected client.

## Development

```text
python -m pytest packages/mne-cpp-mcp/tests -c packages/mne-cpp-mcp/pyproject.toml
```

Set `MNE_CPP_TEST_BIN_DIR` to run optional native synthetic-data tests. Only those
tests require MNE-Python and NumPy to generate and independently verify fixtures.
Set `MNE_CPP_TEST_ARCHIVE` to the official Windows ZIP to exercise offline
extraction, native verification, client setup and a real stdio tool call in an
isolated temporary home. No real client configuration is modified by these tests.
The Python 0.4.0 distribution excludes this preview package.

## Bridge Optimizations

Successful version probes are reused for 60 seconds during analysis, invalidated
when executable file metadata changes. Explicit status checks always probe again.
Executable SHA-256 hashing is streamed off the event loop and cached by file
metadata. This removes repeated bridge overhead, not native algorithm work;
these caches are not a defense against tampering with trusted native binaries.
Invalid input paths fail before launching a native process. Metadata and evoked
summary tools reject truncated output, and evoked results expose `dataset_count`
as a structured integer alongside the original native output.
