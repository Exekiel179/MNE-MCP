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
Testing found that the official 2.3.0 `mne_process_raw` saved unchanged samples
despite filter arguments, and did not export known trigger events. These commands
are deliberately not exposed. See [validation evidence](VALIDATION.md).

There is no general speedup claim here. Equivalent algorithms, thread counts,
numerical tolerances, I/O and process-start overhead must be benchmarked first.

## Install

Use Python 3.12+ in a dedicated environment. Download and extract the official
[MNE-CPP 2.3.0 native release](https://github.com/mne-tools/mne-cpp/releases/tag/v2.3.0)
for your platform, with its Qt libraries. Do not use a browser/Wasm build. The
verified platform is Windows x86_64; macOS/Linux remain untested.

From the MNE-MCP checkout:

```text
python -m pip install ./packages/mne-cpp-mcp
```

This package is not published to PyPI. It does not install MNE-CPP, Qt or MNE-Python.
Keep native executables in a trusted, user-managed directory.

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

The wheel bundles `mne-cpp-analyst`; run
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
The Python 0.4.0 distribution excludes this preview package.
