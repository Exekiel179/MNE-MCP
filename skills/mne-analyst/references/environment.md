# Environment checks

1. Call mne_check_status and record the server Python path and available versions.
2. If MNE is unavailable, stop analysis. Ask for the import error from that exact interpreter.
   Missing packages, binary incompatibility, and unreadable MNE configuration are different failures.
   Do not replace the user's environment or assume every import error means a missing package.
3. Prepare only the dependencies required for the requested workflow:

| Workflow | User-managed libraries |
|---|---|
| Core session | mne, numpy, scipy, matplotlib, pandas |
| ICA / decoding | scikit-learn; python-picard only for Picard |
| Connectivity | mne-connectivity |
| BIDS | mne-bids |
| Automated rejection | autoreject; mne-icalabel only for labeling |
| Source / rendering | nibabel, pyvista as required by the selected tool |
| File readers / exporters | pymatreader, h5io, edfio as required by the format |

Report the missing package and affected feature. Do not run pip from mne_run_code or mutate a
live server's dependencies. When environment changes are authorized, use the reported interpreter
outside the MCP session, restart the client, and check status again. Unrelated available workflows
can continue. Record versions with the exported analysis.

Setup installs the whole skill suite, not these analysis packages. Rerun setup after upgrading
MNE-MCP. Use only skills/tools available in the current client. If isolated subagent review is
unavailable, apply the methodology-critic skill as a separate review pass and disclose that it
was not independent; never invent a reviewer or claim an unperformed validation.
