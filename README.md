# Pyxo No Hassle A/V 8x8 HDMI 4K Matrix Switcher

![No Hassle Audio Video](custom_components/pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher/brand/logo.png)

A standalone, local Home Assistant custom integration for the No Hassle A/V 8×8 HDMI matrix protocol. Each matrix becomes one device with eight native `select` entities. Configure multiple matrices independently, over network UDP or a local RS232 serial port. No YAML, shell commands, cloud accounts, or cloud services are used by the integration.

**Development MVP, version 0.1.0.** Tested in Home Assistant 2026.10.0 with mocked hardware. No live matrix or serial adapter has been tested. The target device is the No Hassle A/V 8x8 HDMI 4K Matrix Switcher; physical unit/firmware compatibility remains untested. Only devices matching the supplied command reference are supported. See [validation](VALIDATION.md).

Product: [No Hassle A/V — 8x8 HDMI 4K Matrix Switcher](https://nohassleav.com/products/8x8-hdmi-4k-hdr-matrix-switcher-18gbps-ultra-yuv-4-4-4-hdcp2-2-60hz-hdmi-2-0b-doby-atmos-hdtv-routing-selector-spdif-audio-control4-savant-home-automation-switch-ip-rs232).

Repository/package name: `no-hassle-av-8x8-hdmi-4k-matrix-switcher`. Home Assistant domain: `pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher`.

## Install

Requires Home Assistant 2026.10 or newer (Python 3.14). For local installation:

1. Copy the `custom_components/pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher` directory into `/config/custom_components/pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher` on the Home Assistant host.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → Pyxo No Hassle A/V 8x8 HDMI 4K Matrix Switcher**.
4. Enter a matrix name and choose `udp` or `serial`. Only the selected transport's fields are used.
5. Name the eight inputs and eight outputs. Leave the unique defaults if desired. Reboot is disabled by default.
6. Add the integration again for each additional matrix.

### HACS installation

1. Open **HACS → three-dot menu → Custom repositories**.
2. Add `https://github.com/pyxo/no-hassle-av-8x8-hdmi-4k-matrix-switcher` and select **Integration**.
3. Find **Pyxo No Hassle A/V 8x8 HDMI 4K Matrix Switcher**, download it, and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration**, select this integration, and complete the setup above.

[Open this repository in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=pyxo&repository=no-hassle-av-8x8-hdmi-4k-matrix-switcher&category=integration)

This integration is distributed as a HACS custom repository; it is not included in HACS's default catalog. Each physical matrix can be added separately after installing the integration once.

## Network or serial

| Connection | Settings |
| --- | --- |
| Network (`udp`) | IP address or hostname, UDP port (default 5000). No TCP, authentication, or newline. |
| Serial (`serial`) | Local serial device path, e.g. `/dev/serial/by-id/...`, `/dev/ttyUSB0`, `/dev/cu.usbserial-...` or `COM3`. Fixed 115200 baud, 8 data bits, no parity, 1 stop bit. |

For a network matrix, reserve its DHCP address or assign a static IP. Setup only enumerates local serial-port metadata and persistent device links; it does not resolve network hosts, open serial devices, probe, route, or reboot hardware. An accepted setup form is not a successful connection test.

For serial, pass the physical RS232 adapter through to the Home Assistant host/container, provide access permissions, and use appropriate matrix wiring. The UI lists detected ports and automatically converts a numbered port such as `/dev/ttyUSB0` to its persistent `/dev/serial/by-id/...` alias when available, with `/dev/serial/by-path/...` as a fallback. Device-ID paths follow the adapter when its numbered port changes; by-path follows the physical USB connection and requires using the same socket. The saved link is opened afresh for each command, so it is never permanently resolved to a numbered port. A missing saved adapter causes an error; the integration never guesses a replacement. If the host supplies neither persistent link, the entered path is retained and its stability cannot be guaranteed: configure a persistent OS mapping before relying on it across reboots. Windows COM and macOS device paths depend on the host's device naming. Other integrations must not own the same serial port. Remote serial proxies are outside this MVP. The manufacturer notes that some control systems need a carriage return; **Append carriage return** is an explicit serial-only option, off by default. UDP always sends the exact ASCII bytes without CR or LF. Serial sends those same bytes unless this option is enabled. Serial ports open only for explicit routing/reboot actions and close after flushing each command. Port opening and adapter control-line behavior still require hardware testing.

## Edit names and connection settings

Use the integration entry's **Configure** button to edit all eight input labels, all eight output labels, and the optional reboot button. Input labels must be unique within a matrix, ignoring case, and all labels must contain 1–100 characters. Two inputs both called “Unassigned” should instead be named “Unassigned 7” and “Unassigned 8”.

Use the entry menu's **Reconfigure** action to change its matrix name, IP/hostname, UDP port, serial path, connection type or serial carriage-return option. Changing settings reloads that entry. The config entry ID identifies the matrix; output entity IDs and device IDs remain stable when connection details or labels change. Custom entity names set directly in Home Assistant's entity registry take precedence over configured output labels. Changing an input label changes the option string used in automations, so update affected automations.

Duplicate normalized network host/port pairs and duplicate serial paths are rejected. Known serial aliases are normalized to persistent links when available. DNS aliases, IP-vs-hostname aliases, and arbitrary custom serial symlinks cannot always be identified as the same physical matrix without hardware identity/readback. Configure each physical matrix once, using one connection type. Entry removal uses the normal Home Assistant entry menu.

## Select an input

Each output offers the eight input labels in physical input order. For example, rename input 3 to `Apple TV 1`, then use:

```yaml
action: select.select_option
target:
  entity_id: select.hdmi_matrix_1_output_1
data:
  option: "Apple TV 1"
```

Entity IDs depend on the names chosen at creation; use the actual entity shown in HA. Outputs work independently, with commands for the same output serialized. Serial commands also share a port lock. Repeating a selection deliberately resends the command: without readback, this is how a user can reassert a route changed externally. There are no polling, retry, startup replay or background hardware commands.

## Saved, assumed routing state

There is **no documented route/status query or acknowledgement format** in the supplied manufacturer file. This integration does not send invented queries and does not claim to know whether a matrix is online.

After a local send completes, the selected input is assumed. Each select exposes `assumed_state: true`, `readback_supported: false`, its physical input/output, and `state_source`:

- `unknown`: no stored input, invalid stored data, local command failure, or a requested matrix reboot.
- `last_command`: the last input sent by this integration, without hardware confirmation.
- `restored`: a last-known input loaded from local HA storage.

The physical input number is persisted through Home Assistant's standard `RestoreEntity` mechanism in `/config/.storage/core.restore_state`. HA saves this JSON file periodically and on orderly shutdown. It is included in normal HA configuration backups; don't edit it manually. A sudden power loss may lose changes since the last save. After an HA restart or integration reload, a valid stored input is restored using the **current label**, without sending anything to the matrix. New outputs start unknown. Removing and re-adding an entry creates a new identity and does not recover the old entry's routes.

Saved state may be stale after the matrix loses power, changes settings, or receives a command from its front panel, remote, web UI, another controller or another HA installation. Select an input again to reassert it. This MVP does not automatically restore the physical matrix's routes. Enabling the reboot option only exposes a button; pressing that button sends the documented reboot command and clears all eight assumptions, including saved values on the next HA save.

A DNS/network/serial error is reported as a failed action and makes the affected output unknown. A successful local send does not prove remote delivery. There is no “connected” diagnostic, firmware sensor, factory reset, power control, or all-outputs action.

## Correct protocol mapping

The initial project specification assumed sequential output addresses. The manufacturer's uploaded `8x8 HDMI Matrix.txt` corrects it:

| Physical output | Wire address |
| --- | --- |
| 1 | `00` |
| 2 | `01` |
| 3 | `02` |
| 4 | `03` |
| 5 | `11` |
| 6 | `12` |
| 7 | `13` |
| 8 | `14` |

Physical inputs 1–8 use wire values `00`–`07`. Output 5 selecting input 8 sends exactly `@T 11 07 !`. **`@T 04 YY !` switches ALL outputs; `04` must never be used as physical output 5.** The client exposes physical port numbers 1–8 and provides no raw-command or broadcast API. Reboot is `@T 50 !`. See [protocol evidence](docs/PROTOCOL.md).

## Troubleshooting

- **No visible switching:** check the connection choice, address/port or serial path, wiring, permissions, and model compatibility. UDP has no confirmed reply; an assumed HA state does not establish reachability.
- **Wrong room changes:** verify the physical cabling and output labels. Output 5 is wire address `11`, not `04`.
- **Names don't change:** a user-assigned HA entity name overrides the integration's output label; clear that custom name if desired. Entity IDs intentionally stay stable.
- **State differs from the matrix:** no readback exists in this MVP. Reselect the actual desired input.
- **Serial timeout or missing device:** verify adapter passthrough and permissions from the HA host, use a stable device path, and ensure nothing else is using the port. The documented CR caveat may require the explicit serial-only setting.
- **Optional reboot:** disruptive; only use the button when you intend to restart that matrix. No automatic reboot or retries occur.

## Development and verification

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

Tests use real Home Assistant 2026.10.0 flow/entity/storage handling, mocked UDP sockets and mocked serial transports. They do not operate hardware. CI repeats these checks. Manual installation/UI display, installation through HACS on a deployed HA host, actual UDP delivery, RS232 wiring/terminators, and live switching require separate validation with explicit user authorization.

The implementation follows Home Assistant's [options flow](https://contributors.home-assistant.io/core/integrations/options-flow/), [reconfiguration](https://contributors.home-assistant.io/core/integrations/reauth-and-reconfigure/), [local branding](https://contributors.home-assistant.io/core/integrations/brands/), and [serialx guidance](https://contributors.home-assistant.io/blog/2026/04/27/pyserial-to-serialx/), plus the [HACS integration layout](https://www.hacs.dev/docs/publish/integration/).

## AI assistance and branding

This integration was developed with AI assistance (OpenAI Codex), including code, tests and documentation. It requires human review and live hardware validation before relying on it in a production system. Pyxo is an independent custom integration, not an official No Hassle A/V or Home Assistant product. The supplied No Hassle A/V logo belongs to its owner and is included to identify supported equipment; it is not covered by the code license. The wide logo is preserved as supplied; the square A/V icon is an AI-assisted adaptation for the HA UI.
