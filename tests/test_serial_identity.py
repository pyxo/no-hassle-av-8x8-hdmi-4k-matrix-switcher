"""Persistent serial links survive numbered-port changes without selecting a neighbor."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher import (
    serial_identity as identity,
)
from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.const import DOMAIN


def test_prefer_identity_over_location_and_keep_link_after_reboot(tmp_path, monkeypatch):
    by_id = tmp_path / "by-id"
    by_path = tmp_path / "by-path"
    by_id.mkdir()
    by_path.mkdir()
    monkeypatch.setattr(identity, "SERIAL_LINK_DIRS", (by_id, by_path))
    original = tmp_path / "ttyUSB0"
    original.touch()
    persistent = by_id / "usb-adapter-A"
    persistent.symlink_to(original)
    (by_path / "usb-socket-1").symlink_to(original)
    saved = identity.preferred_serial_path(str(original))
    assert saved == str(persistent)
    # A reboot reassigns the adapter to ttyUSB1; ttyUSB0 may now be someone else.
    reassigned = tmp_path / "ttyUSB1"
    reassigned.touch()
    persistent.unlink()
    persistent.symlink_to(reassigned)
    assert identity.preferred_serial_path(saved) == saved
    assert persistent.resolve() == reassigned
    # Disconnecting doesn't cause fallback to the old ttyUSB0 or another adapter.
    persistent.unlink()
    assert identity.preferred_serial_path(saved) == saved


def test_location_fallback_and_missing_mapping(tmp_path, monkeypatch):
    by_path = tmp_path / "by-path"
    by_path.mkdir()
    monkeypatch.setattr(identity, "SERIAL_LINK_DIRS", (tmp_path / "absent-by-id", by_path))
    target = tmp_path / "ttyUSB2"
    target.touch()
    assert identity.preferred_serial_path(str(target)) == str(target)
    link = by_path / "socket-A"
    link.symlink_to(target)
    assert identity.preferred_serial_path(str(target)) == str(link)


async def test_picker_lists_stable_paths_and_enumeration_failure(hass):
    port = SimpleNamespace(device="/dev/ttyUSB0", product="RS232 adapter", serial_number="A123")
    with (
        patch("serialx.async_list_serial_ports", AsyncMock(return_value=[port])),
        patch.object(identity, "preferred_serial_path", return_value="/dev/serial/by-id/adapter-A"),
    ):
        choices = await identity.async_serial_choices(hass)
    assert choices[0]["value"] == "/dev/serial/by-id/adapter-A"
    assert "A123" in choices[0]["label"]
    with patch("serialx.async_list_serial_ports", AsyncMock(side_effect=OSError("unavailable"))):
        assert await identity.async_serial_choices(hass) == []


async def test_flow_saves_persistent_path_and_prevents_alias_duplicate(hass):
    path = "/dev/serial/by-id/adapter-A"
    with patch.object(identity, "preferred_serial_path", return_value=path):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={"name": "Matrix", "connection": "serial", "serial_path": "/dev/ttyUSB0"},
        )
        with patch(f"custom_components.{DOMAIN}.async_setup_entry", AsyncMock(return_value=True)):
            result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
            await hass.async_block_till_done()
        assert result["data"]["serial_path"] == path
        duplicate = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={"name": "Duplicate", "connection": "serial", "serial_path": "/dev/ttyUSB1"},
        )
        assert duplicate["reason"] == "already_configured"
