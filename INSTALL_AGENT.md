# Install MNE-MCP for the user

This is the installation entrypoint for a coding agent with terminal access.
Install the lightweight MCP interface and its complete skill suite into the user's existing
Python environment, reusing MNE when available. Follow the user's chosen client, interpreter, location, and execution permissions.

## 1. Locate the checkout and environment

Use an existing MNE-MCP checkout when the user provides one. Otherwise clone
https://github.com/Exekiel179/MNE-MCP.git at the latest published release tag into an appropriate user workspace and read this file
from that checkout. Do not overwrite an existing directory or discard local changes.
Do not substitute an older PyPI release for the checkout described here.

Prefer the user's specified Python interpreter. Otherwise inspect the active environment,
the checkout's existing .venv, and environment-manager listings such as conda env list when
available. Do not scan the whole disk. If no MNE environment exists, use the user's selected Python 3.12+ environment; prefer a dedicated venv over system Python. Creating a project-local venv is a normal installation step when needed.
Use the absolute path of the interpreter that imports MNE. Keep virtual-environment symlink
paths intact; resolving them to the base interpreter can select the wrong environment.

## 2. Read-only preflight

From the checkout, run:

```text
<python> scripts/install.py --check --json --python <mne-python>
```

Replace placeholders with actual executable paths and quote them using the host shell's rules.
For PowerShell, use its & invocation operator before a quoted executable path.
The JSON reports the selected Python, its version, core import results, and detected clients.
Exit code 0 means the environment is ready; 1 means it needs attention.

Python 3.12 is the minimum and current full-test baseline, not an upper limit.
Do not reject Python 3.13+ solely because of its version. Installation eligibility
does not establish scientific compatibility: verify the intended workflow and
report actual dependency failures without silently disabling acceleration.
Core analysis uses mne, numpy, scipy,
matplotlib and pandas. The interpreter also needs pip. Preserve the actual exception:
missing packages, incompatible binaries and unreadable configuration require different fixes.
If Python 3.12+ and pip are available but core libraries are missing, continue to installation:
the installer automatically installs missing mne/numpy/scipy/matplotlib/pandas with that interpreter's pip.
If Python itself is absent, explain that prerequisite. Do not install the complete test lock file.

## 3. Select the intended client

Use the client's identity from the user's request or current host context: codex, claude,
psyclaw, or opencode. Pass --clients explicitly for a single-client request.
Omitting --clients now registers all four clients and installs skills for each, even if
the clients are not yet installed. Use that default only when the user wants all clients.
The optional --clients auto mode still requires exactly one detected client.

## 4. Install and register

```text
<python> scripts/install.py --python <mne-python> --clients <client>
```

This checks prerequisites, installs the checkout using the selected interpreter's pip,
installs absent core analysis libraries, checks status, and runs setup with that same interpreter.
It preserves MNE preferences and does not request upgrades of already importable libraries.
Pip may resolve transitive dependencies when adding a missing package. Broken imports (such as
permission errors or binary incompatibility) stop installation and require diagnosis.
Do not run pip from inside mne_run_code or pipe a downloaded script into a shell.

Setup installs all 14 skills and references into the selected client's skills directory.
Codex uses CODEX_HOME/skills (default ~/.codex/skills); Claude uses ~/.claude/skills;
opencode uses XDG_CONFIG_HOME/opencode/skills (default ~/.config/opencode/skills).
PsyClaw uses ~/.psyclaw/skills and a standalone MCP record at ~/.psyclaw/mcp/mne.json.
Do not write a Claude-style mcpServers object there. Setup explicitly enables/trusts
the MNE server selected by the user, without adding broad tool-policy bypasses.
Existing skills and client configurations are backed up before updates.
Claude additionally receives the methodology-review subagent. Other clients use its skill.
Do not delete other installed skills or claim a separate reviewer ran when it did not.

## 5. Verify and report

Require a successful script exit and inspect the setup output for the configured client and
complete skill list. Report the absolute interpreter path, client, skill location, and any errors.
Setup tests a real stdio handshake, tool discovery and mne_check_status; for PsyClaw,
it also tests the saved record. A missing MNE backend is reported separately from
a successful MCP connection. Retest without registration using
`python -m mne_mcp verify --client psyclaw`.
Do not equate the standalone setup test with the user's already-running client session.
Ask the user to restart the target client (PsyClaw also supports /reload). If tools can reload in the current host, call
mne_check_status after reload and verify the reported interpreter and MNE version.
Report "installed; client restart pending" until that live check actually succeeds.
In PsyClaw, discover the mne server through psyclaw_mcp action=list, then call
mne_check_status using the exposed bridge schema. A project .psyclaw/mcp entry with
id=mne overrides the user entry; check it when the live Python path differs.

For updates, repeat installation and setup from the intended checkout/version. Optional analysis
libraries are checked for the user's requested workflow; do not install them all in advance.
On failure, stop at the failing stage and diagnose its output instead of switching install methods.
