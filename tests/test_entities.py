"""Exercise entities, persistence and actions using the real Home Assistant runtime."""

import pytest
from homeassistant.core import State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import restore_state
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_restore_state_shutdown_restart,
)

from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.client import (
    MatrixCommunicationError,
)
from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.const import DOMAIN
from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.model import labels
from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.select import RouteStoredData


async def setup(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def selectors(hass):
    return sorted(hass.states.async_all("select"), key=lambda s: s.attributes["physical_output"])


async def select(hass, entity_id, option):
    await hass.services.async_call(
        "select", "select_option", {"entity_id": entity_id, "option": option}, blocking=True
    )


async def test_eight_selects_no_startup_io_and_safe_output_five(hass, entry, hardware):
    await setup(hass, entry)
    states = selectors(hass)
    assert len(states) == 8
    assert not hass.states.async_all("button")
    assert all(s.state == "unknown" for s in states)
    assert all(s.attributes["assumed_state"] for s in states)
    assert all(s.attributes["readback_supported"] is False for s in states)
    hardware[0].assert_not_awaited()
    hardware[1].assert_not_awaited()
    await select(hass, states[4].entity_id, "Input 8")
    hardware[0].assert_awaited_once_with(5, 8)
    state = hass.states.get(states[4].entity_id)
    assert state.state == "Input 8"
    assert state.attributes["state_source"] == "last_command"
    assert states[0].state == "unknown"
    registry = er.async_get(hass)
    assert registry.async_get(states[4].entity_id).unique_id == f"{entry.entry_id}_output_5"
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    assert devices[0].identifiers == {(DOMAIN, entry.entry_id)}


async def test_local_failure_invalidates_assumption(hass, entry, hardware):
    await setup(hass, entry)
    entity_id = selectors(hass)[0].entity_id
    await select(hass, entity_id, "Input 2")
    hardware[0].side_effect = MatrixCommunicationError("DNS failed")
    with pytest.raises(HomeAssistantError, match="DNS failed"):
        await select(hass, entity_id, "Input 3")
    assert hass.states.get(entity_id).state == "unknown"
    assert hass.states.get(entity_id).attributes["state_source"] == "unknown"


async def test_save_restore_and_rename_inputs(hass, entry, hardware, hass_storage):
    await setup(hass, entry)
    entity_id = selectors(hass)[4].entity_id
    await select(hass, entity_id, "Input 3")
    await async_mock_restore_state_shutdown_restart(hass)
    saved = hass_storage["core.restore_state"]["data"]
    output = next(s for s in saved if s["state"]["entity_id"] == entity_id)
    assert output["extra_data"] == {"input_number": 3}
    assert await hass.config_entries.async_unload(entry.entry_id)
    hass.config_entries.async_update_entry(
        entry, options=labels({"input_3": "Apple TV", "output_5": "Office"})
    )
    await setup(hass, entry)
    state = hass.states.get(entity_id)
    assert state.state == "Apple TV"
    assert state.attributes["state_source"] == "restored"
    assert state.attributes["physical_input"] == 3
    # Restoring doesn't replay commands to hardware.
    hardware[0].assert_awaited_once_with(5, 3)
    assert er.async_get(hass).async_get(entity_id).original_name == "Office"


@pytest.mark.parametrize("value", [None, True, 0, 9, "3"])
async def test_invalid_saved_index_is_unknown(hass, entry, hardware, value):
    restore_state.async_get(hass).last_states["select.matrix_1_output_1"] = (
        restore_state.StoredState(
            State("select.matrix_1_output_1", "Old label"), RouteStoredData(value), dt_util.utcnow()
        )
    )
    await setup(hass, entry)
    assert selectors(hass)[0].state == "unknown"
    hardware[0].assert_not_awaited()


async def test_optional_reboot_clears_saved_states(hass, entry, hardware, hass_storage):
    hass.config_entries.async_update_entry(entry, options=labels({"show_reboot": True}))
    await setup(hass, entry)
    await select(hass, selectors(hass)[0].entity_id, "Input 2")
    button = hass.states.async_all("button")[0]
    await hass.services.async_call(
        "button", "press", {"entity_id": button.entity_id}, blocking=True
    )
    hardware[1].assert_awaited_once()
    assert all(s.state == "unknown" for s in selectors(hass))
    await restore_state.RestoreStateData.async_save_persistent_states(hass)
    assert all(
        s["extra_data"]["input_number"] is None
        for s in hass_storage["core.restore_state"]["data"]
        if s["state"]["entity_id"].startswith("select.")
    )


async def test_multiple_udp_and_serial_matrices_are_independent(hass, entry, hardware):
    second = MockConfigEntry(
        domain=DOMAIN,
        title="Matrix 2",
        data={"name": "Matrix 2", "connection": "serial", "serial_path": "/dev/ttyUSB0"},
        options=labels({}),
    )
    second.add_to_hass(hass)
    await setup(hass, entry)
    # Initial domain setup also loads other entries registered before setup.
    await hass.async_block_till_done()
    assert len(selectors(hass)) == 16
    registry = er.async_get(hass)
    first_entity = next(
        s.entity_id
        for s in selectors(hass)
        if registry.async_get(s.entity_id).unique_id == f"{entry.entry_id}_output_8"
    )
    second_entity = next(
        s.entity_id
        for s in selectors(hass)
        if registry.async_get(s.entity_id).unique_id == f"{second.entry_id}_output_8"
    )
    await select(hass, first_entity, "Input 3")
    await select(hass, second_entity, "Input 7")
    hardware[0].assert_awaited_once_with(8, 3)
    hardware[2].assert_awaited_once_with(8, 7)
    assert hass.states.get(first_entity).state == "Input 3"
    assert hass.states.get(second_entity).state == "Input 7"
    await hass.config_entries.async_unload(entry.entry_id)
    assert hass.states.get(second_entity).state == "Input 7"
