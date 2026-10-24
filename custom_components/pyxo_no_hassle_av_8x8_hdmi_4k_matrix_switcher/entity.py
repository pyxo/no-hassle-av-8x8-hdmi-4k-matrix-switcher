"""Shared device identity independent of host, port and labels."""

from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN


class PyxoEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry):
        self.entry = entry
        self.matrix = entry.runtime_data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data["name"],
            manufacturer="No Hassle A/V",
            model="8x8 HDMI 4K Matrix Switcher",
        )
