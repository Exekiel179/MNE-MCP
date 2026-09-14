---
name: mne-cpp-analyst
description: Inspect native FIFF files through the MNE-CPP MCP preview, verify backend availability, and explain validated capability boundaries. Use when the user explicitly selects MNE-CPP.
---

# MNE-CPP Inspection

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
Do not claim C++ is universally faster; compare equivalent algorithms including
process startup and file I/O costs.
