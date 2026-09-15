---
name: mne-cpp-analyst
description: Set up or inspect native FIFF files through the MNE-CPP MCP preview, verify backend availability, and explain validated capability boundaries. Use when the user explicitly selects MNE-CPP.
---

# MNE-CPP Inspection

## Installation Requests

Use Python 3.12+; no MNE-Python dependency is needed. For a source checkout,
install the light bridge with `python -m pip install ./packages/mne-cpp-mcp`.
Do not assume this preview has been published to PyPI.

When the user asks to install/configure it, identify the selected client and an
existing absolute data directory. Run with the selected environment interpreter:
`python -m mne_cpp_mcp setup --data-dir "D:/research/data"`.
Replace the example directory with the user's choice. The console shortcut is
`mne-cpp-mcp setup`. Exactly one detected client is selected automatically;
otherwise add `--clients` with the user's choice, never all clients by default.
Setup reuses `--bin-dir` or `MNE_CPP_BIN_DIR` if provided; otherwise it reuses or
installs the verified official Windows x86_64 runtime, registers selected clients
and installs this skill. A broken configured runtime is an error, not permission
to reinstall. For existing native tools add `--bin-dir "C:/tools/mne-cpp/bin"`. Other platforms require
user-managed native tools and are untested. `--check` is a read-only preflight;
exit code 1 for missing tools is expected. Offline `--archive` accepts the same
official ZIP and enforces the fixed checksum. The old `--install-native` flag and
`python -m mne_cpp_mcp.server` entrypoint remain compatible.

Do not bypass a checksum failure or overwrite an unmanaged native directory.
Report backup paths and request a client restart. Client registration does not
export environment variables into the current terminal. Missing-dependency
diagnosis alone is not permission to install or rewrite client settings.

## Analysis Requests

Check `mne_cpp_check_status` first. `ready` means verified inspection executables
are available, not that a complete scientific pipeline is supported. Use reported
capability limits even if upstream help advertises more.

- `mne_cpp_inspect_fiff`: prefer block-only inspection; full metadata may contain
  participant information visible to the AI client.
- `mne_cpp_read_metadata`: sampling frequency and Nyquist in Hz, not a quality
  assessment or a safe cutoff without transition-band review.
- `mne_cpp_evoked_summary`: descriptive evoked metadata; nave counts averages and
  must not be treated as independent participants.
- `mne_cpp_get_help`: installed CLI help, not proof of scientific correctness.

Use absolute paths within MNE_CPP_DATA_DIR. Do not change the directory boundary
or client configuration to access a rejected path without user approval.
Do not install dependencies during an analysis call.

Filtering and trigger export through mne_process_raw 2.3.0 failed validation and
are not exposed. ICA, source analysis, decoding and real-time streaming are also
outside this preview. Explain the limitation and propose MNE-Python MCP for
analysis; do not silently substitute it when the user requests native C++.

Separate observed metadata, backend/version, limitations and proposed next
analysis. Never turn metadata into biological or statistical conclusions.
Use `dataset_count` for the verified evoked dataset count, not participant count.
Truncated inspection is incomplete evidence; metadata/evoked tools fail rather
than interpret a truncated response. Status probes explicitly refresh; analysis
calls briefly cache compatible executable versions to reduce startup overhead.
Do not claim C++ is universally faster; compare equivalent algorithms including
process startup and file I/O costs.
