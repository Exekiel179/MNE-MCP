# Install MNE-CPP MCP With an Agent

Suggested user request:

> Install the MNE-CPP MCP from this checkout in my Python environment, install
> its verified native runtime if missing, configure my selected MCP client and
> companion skill, and verify it. Use my chosen data directory as the access
> boundary. Follow packages/mne-cpp-mcp/INSTALL_AGENT.md.

## Scope

This is a read-only FIFF inspection preview, not the full MNE-Python backend.
Do not promise filtering, ICA, trigger export, or a general C++ speed advantage.
The package is not yet on PyPI: install from a checkout or built wheel, without
inventing a released package version. Do not install MNE-Python for this bridge.

## Procedure

1. Identify the Python 3.12+ environment, intended client (`codex`, `claude`, or
   `opencode`), and existing absolute data directory. Ask for the client or data
   directory if unclear; do not authorize all files or all clients by default.
2. Use that interpreter for `python -m pip install ./packages/mne-cpp-mcp` from
   the repository root. Do not globally install tools or change system PATH.
3. Run `python -m mne_cpp_mcp setup --data-dir "D:/research/data" --check`,
   substituting the authorized data directory. Setup selects a client only when
   exactly one configuration file or executable is detected; otherwise add
   `--clients` with the user's choice. For known existing tools add `--bin-dir`;
   `MNE_CPP_BIN_DIR` is also respected. Check mode does not install; missing tools are expected
   to produce exit code 1. Distinguish missing files from permissions, wrong
   platform, incompatible version and broken Qt dependencies.
4. After authorization for installation/client setup, run the same setup command
   without `--check`. No `--install-native` flag is required. Without a provided
   native path, setup reuses or installs the managed runtime. On Windows x86_64 it uses the official
   2.3.0 dynamic ZIP, fixed SHA-256 verification and an isolated per-user path.
   Offline `--archive` accepts only that same official ZIP. For macOS/Linux use
   an existing native `--bin-dir`; do not claim these platforms are validated.
5. Read the JSON result and retain backup paths. If a network or checksum error
   occurs, stop and explain it; do not disable checksum validation, replace the
   source, alter proxy settings or repeatedly reinstall. If setup partially wrote
   one client's files before an I/O failure, report the partial state explicitly.
6. Ask the user to restart selected clients, then call `mne_cpp_check_status`.
   Require `ready == true`, and verify an authorized FIFF file with block-only
   inspection when one is provided. Never upload a recording or reveal detailed
   participant metadata merely to prove installation.

## Configuration

Setup binds the current interpreter's absolute path and passes `MNE_CPP_BIN_DIR`
and `MNE_CPP_DATA_DIR` to the child process. It does not mutate the calling shell.
Claude Code uses `~/.claude.json` and `~/.claude/skills`; Codex uses
`$CODEX_HOME/config.toml` and `$CODEX_HOME/skills` (default `~/.codex`); opencode uses
`$XDG_CONFIG_HOME/opencode` (default `~/.config/opencode`). This does not configure
Claude Desktop or an unselected client.

Backups are sibling files named `.backup.<timestamp>`. Repeat setup preserves
unchanged files and user-added skill files. Native installations at an existing
unmanaged destination are never overwritten. CLI terminal status requires the
two environment variables in that terminal; registration alone does not set them.
