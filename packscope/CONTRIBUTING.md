# Contributing to PackScope

Thank you for improving PackScope. This project aims to make an exploratory research workflow more transparent and reproducible. Contributions must preserve the difference between device-derived values, raw physiological samples, calibrated gaze coordinates, and derived metrics.

## Development setup

Use Python 3.11 or later. Create an isolated environment, install the development extras, and run the test and lint suites before opening a pull request.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,reporting]'
pytest
ruff check .
```

Hardware-specific extras remain optional. A contributor should not need a headset, camera, Bluetooth stack, native LSL library, or proprietary SDK to run the default tests.

## Code and review requirements

Use type hints for public APIs and document non-obvious signal-processing or protocol decisions. Preserve SPDX headers in Python source files. Add offline unit tests for parsers, timestamp behavior, unavailable results, and error paths. Do not add vendor SDK binaries, captured participant data, credentials, model weights without a redistribution audit, or proprietary dependencies to this repository.

A new device adapter must declare capabilities, timestamp provenance, units, channel labels, raw-versus-processed status, sample/dropout behavior, and license constraints. A new EEG feature must define its inputs, frequency bounds, reference/montage assumptions, quality gates, artifact policy, unavailable state, and interpretive limits. New gaze adapters must explicitly document calibration, validation, display coordinate origin, mirror/crop policy, and drift checks.

## Pull requests

Describe the problem, hardware and OS tested, dependency versions, test command output, and any scientific or privacy limitation introduced by the change. Keep unrelated formatting changes out of functional pull requests. By submitting a contribution, you agree to license it under Apache License 2.0, unless the maintainers agree to different terms in writing.

## Reporting vulnerabilities and privacy concerns

Do not file public issues containing participant data, raw video, serial numbers, access tokens, or unredacted study exports. Report a potential security or privacy issue privately to the maintainers listed in the repository security policy after one is established.
