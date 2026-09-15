# Native Validation

## GitHub Preview Release Verification (2026-09-15)

The release candidate passed **49 tests**, with no skips, in 17.72 seconds on
Windows x86_64 using the existing project Python 3.12 environment. This run
included the official network download/digest, offline installation, real native
synthetic FIFF workflows and stdio connection checks. The existing upstream
Pydantic-settings warning remains; no live client configuration was changed.

An initial run encountered a Windows directory-rename PermissionError in the
atomic-install test (47 passed, 1 failed, 1 download test skipped). The complete
rerun passed without code changes. No retry or permission-bypass logic was added;
intermittent filesystem interference remains a documented installation risk.

Both wheel and source archive build successfully. The wheel contains the short
module entrypoint, setup implementation and companion skill. This release does
not add PsyClaw registration or full scientific analysis to the C++ bridge.

## Installer and Bridge Verification (2026-09-15)

Final Windows x86_64 run: **39 passed**, no skipped tests, in 21.18 seconds.
One existing MCP/Pydantic-settings forward-reference warning remains; live
stdio initialization, tool listing and native metadata calls pass.

```powershell
$env:MNE_CPP_TEST_BIN_DIR = "<absolute native bin directory>"
$env:MNE_CPP_TEST_ARCHIVE = "<absolute official Windows dynamic ZIP>"
$env:MNE_CPP_TEST_DOWNLOAD = "1"
python -m pytest packages/mne-cpp-mcp/tests -c packages/mne-cpp-mcp/pyproject.toml -p no:cacheprovider
```

Evidence includes the actual official network download and matching release
asset SHA-256, offline extraction into an isolated directory, native executable
verification, generated Claude Code/Codex/opencode configurations, companion
skill installation/backups and repeat-run idempotence. A subprocess launched
using the generated Codex entry reads a synthetic FIFF fixture at 200 Hz through
the real stdio protocol. Real user client settings were not modified.

The official Windows dynamic archive digest was independently checked against
the GitHub v2.3.0 release API:
`98becc6bdc095f2a682836f64bb25fa7963e70a7244331ae9daf73025478d5c0`.
Tests also reject invalid configuration, archive traversal/symlinks, checksum
mismatch, unsupported arguments and interpretation of truncated native output.

Repeated analysis calls reduce version subprocess launches from two per call to
two per cache fill; explicit status, changed executable metadata and expiration
invalidate that reuse. This is a tested call-count improvement, not an algorithm
speed benchmark. Existing timeout/cancellation and synthetic evoked tests pass.

The source distribution and wheel build successfully. The wheel was installed
into an isolated project directory; its own entrypoint reported `ready: true`
and found the bundled skill. No MNE/NumPy/SciPy import is required at startup.
macOS/Linux installation and real desktop-client discovery are not validated.
One intermediate Windows directory-rename permission error did not recur in
two subsequent full native runs; no permission bypass/retry logic was added.

The read-only questions in `evaluations.xml` target the synthetic fixtures from
`test_native_fiff_workflow`. Their expected values are grounded in native test
outputs. They are an agent evaluation set, not a completed model evaluation;
no paid external model run was performed.

## Scientific Baseline

Tested against official MNE-CPP v2.3.0 Windows dynamic x86_64 binaries.
Downloaded from the upstream GitHub release, extracted locally with its Qt DLLs.
No global installation or upstream source modifications were made.

## Blocking Findings

Synthetic raw fixture: 200 Hz sampling, 60 seconds, EEG channel equal to
`1e-6 * (sin(2*pi*10*t) + sin(2*pi*70*t))`, plus a stimulus channel containing
codes 1 and 2 at sample indices 200 and 800.

Calling `mne_process_raw --highpass 1 --lowpass 40 --highpassw 0.5 --lowpassw 5
--filtersize 8192 --save output_raw.fif` returned exit code 0. Independently
reading input/output with MNE-Python gave maximum absolute sample difference
**0.0**, including the out-of-band 70 Hz component. The tagged upstream
[batchprocessor.cpp](https://github.com/mne-tools/mne-cpp/blob/v2.3.0/src/tools/preprocessing/mne_process_raw/batchprocessor.cpp)
passes raw data directly to `MNE::save_raw` without applying `settings.filter`.
Therefore this bridge does not expose a filter tool.

`--eventsout events.fif --digtrig STI014 --filteroff` returned 0 but logged
`0 events found` and generated no events file for the known-trigger fixture.
Do not infer all MNE-CPP event APIs are broken from this single case. It is
sufficient to block this CLI workflow until diagnosed and verified.

Processing executable SHA-256 used for these checks:
`37710d7665aaf50389641aa987f010070a65a27c8bf37f5c0601f9dd6aef85b5`.

## Boundaries

The preview's tests verify native block inspection, 200 Hz sampling metadata,
and an evoked fixture with two EEG channels, nave=12, time range -0.100 to 0.400 s.
They also exercise a live stdio MCP session, reject unlisted executables and
out-of-scope paths, cap native output, and verify process exit after cancellation
or timeout. MNE-Python is used only to create independent test fixtures.

Passing `--version` and `--help` is not scientific validation. Status reports
both the supported preview scope and blocked capabilities. No performance
comparison or full MNE-CPP analysis coverage is claimed. A future processing
backend needs a verified upstream repair or a compiled adapter against the
native library, followed by signal-level regression tests.
