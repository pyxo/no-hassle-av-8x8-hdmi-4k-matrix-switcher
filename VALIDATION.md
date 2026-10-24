# Validation record

Date: October 24, 2026. Version: 0.1.1.

## Verified against the actual uploaded file

The full manufacturer attachment `8x8 HDMI Matrix.txt` was retrieved from the referenced conversation and read before implementation. It establishes ASCII UDP on port 5000, serial at 115200 8N1, the mapping `00,01,02,03,11,12,13,14` for physical outputs 1–8, input indexes `00`–`07`, `04` as all outputs, and `@T 50 !` as reboot. Its carriage-return caveat is documented and exposed only as an explicit serial option. The inconsistent single-line spacing is recorded in `docs/PROTOCOL.md`.

The source contains no route/status/firmware query or response specification. No query or readback parser was invented. Factory reset, power and all-output control are not exposed.

## Verified by automated tests

- 131 pytest cases passed on Python 3.14.8 with Home Assistant 2026.10.0 and pytest-homeassistant-custom-component 0.13.371.
- All 64 route combinations use the correct bytes, including physical output 5. No physical route uses all-output address `04`; no UDP newline is appended.
- Port/index/host validation; normalized hostnames and IPv6; DNS failure, empty resolution, actual timeout, send errors, and cancellation cleanup.
- Serial transport's exact baud/data/parity/stop-bit arguments, route/reboot bytes, explicit optional CR, errors, cancellation cleanup, and local-path validation.
- Partial-name regression tests verify blank, whitespace-only and omitted names use physical-port defaults in setup and options; clearing existing names resets defaults, while duplicate custom input names are still rejected.
- Real HA config/options/reconfigure flow manager, label persistence and validation, multiple UDP/serial entries, duplicate endpoint protection and stable entry identity.
- Eight real SelectEntities per entry, native select actions, physical numbering, correct device/entity registry identities, optional reboot, failure-to-unknown behavior, and independent matrix state.
- HA restore-state serialization in the storage test fixture and simulated shutdown/restart followed by integration reload: the numeric input is restored with a changed label and no hardware replay. Invalid restored values stay unknown. Reboot clears the values that will be saved.
- Persistent-serial tests verify by-id preference over by-path, raw-to-persistent conversion in the setup flow, alias duplicate prevention, missing-adapter behavior, and simulated ttyUSB0 → ttyUSB1 reassignment without changing the stored link.
- Concurrency tests show per-output ordering, independent output routing and reboot waiting for active routes.
- Ruff lint and format checks passed.

All UDP socket operations and serial device operations were mocked. HA storage writes were validated through its standard storage test fixture; this is not a physical HA host reboot. No live matrix address was resolved or contacted, and no serial device was opened during development.

## Implemented but not yet verified on hardware or deployed HA

- Real routing across all 64 combinations on each physical matrix.
- Reachability of either matrix, Matrix 2's address/port, physical unit/firmware compatibility, and any device replies.
- Serial adapter/wiring, device permissions, open/close control-line behavior, and whether CR is needed.
- Manual UI rendering and logo appearance in a deployed HA frontend.
- State survival across an actual HA restart; abrupt host power loss can lose changes since HA's last periodic restore-state save.
- Actual matrix reboot behavior. The reboot button was tested using a mock only.
- Installation through HACS on an actual Home Assistant host and manual UI setup. Repository publication and release metadata are checked separately during publishing; they do not establish hardware compatibility.

These require separate authorization and a controlled hardware session. No live tests are implied by passing software tests.
