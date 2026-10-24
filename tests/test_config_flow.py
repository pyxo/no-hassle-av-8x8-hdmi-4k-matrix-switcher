"""Actual Home Assistant flow manager, no network or serial activity."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.const import DOMAIN
from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.model import labels


async def test_setup_labels_and_two_matrices(hass):
    for number, connection in enumerate(
        [
            {"connection": "udp", "host": "192.0.2.10", "port": 5000},
            {
                "connection": "serial",
                "serial_path": "/dev/serial/by-id/matrix-2",
                "append_cr": True,
            },
        ],
        1,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["type"] == FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"name": f"Matrix {number}", **connection}
        )
        assert result["step_id"] == "labels"
        with patch(
            "custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.async_setup_entry",
            return_value=True,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], labels({"input_1": "Kodi", "output_5": "Office"})
            )
            await hass.async_block_till_done()
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["options"]["input_1"] == "Kodi"
        assert result["options"]["output_5"] == "Office"
        assert result["data"]["connection"] == connection["connection"]
    assert len(hass.config_entries.async_entries(DOMAIN)) == 2


async def test_duplicate_and_invalid_connection(hass, entry):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"name": "Test", "host": "http://matrix"}
    )
    assert result["errors"] == {"base": "invalid_connection"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Test", "host": "MATRIX.EXAMPLE.", "port": 5000}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_invalid_labels(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"name": "Test", "host": "192.0.2.1"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], labels({}) | {"input_1": "Same", "input_2": "same"}
    )
    assert result["errors"] == {"base": "invalid_labels"}


async def test_options_and_reconfigure_preserve_identity(hass, entry):
    original_id = entry.entry_id
    original_unique = entry.unique_id
    result = await hass.config_entries.options.async_init(entry.entry_id)
    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            labels({"input_1": "Shield", "output_1": "Family Room", "show_reboot": True}),
        )
        await hass.async_block_till_done()
        reload.assert_awaited_once_with(entry.entry_id)
    assert entry.options["input_1"] == "Shield"
    assert result["type"] == FlowResultType.CREATE_ENTRY
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id}
    )
    with patch.object(hass.config_entries, "async_reload", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"name": "Renamed", "connection": "serial", "serial_path": "/dev/ttyUSB0"},
        )
        await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["connection"] == "serial"
    assert entry.title == "Renamed"
    assert entry.entry_id == original_id
    assert entry.unique_id == original_unique
    assert entry.options["input_1"] == "Shield"


async def test_reconfigure_cannot_duplicate(hass, entry):
    other = MockConfigEntry(
        domain=DOMAIN, data={"name": "Other", "connection": "serial", "serial_path": "/dev/ttyUSB0"}
    )
    other.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}, data=dict(other.data)
    )
    assert result["errors"] == {"base": "already_configured"}
