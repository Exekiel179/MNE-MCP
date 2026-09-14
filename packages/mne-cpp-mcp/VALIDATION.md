# Native Validation

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
