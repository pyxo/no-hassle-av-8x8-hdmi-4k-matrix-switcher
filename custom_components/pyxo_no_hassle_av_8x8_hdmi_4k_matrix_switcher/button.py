"""Optional reboot button, only present when explicitly enabled in UI."""

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .client import MatrixCommunicationError
from .const import SHOW_REBOOT
from .entity import PyxoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.options.get(SHOW_REBOOT, False):
        async_add_entities([PyxoReboot(entry)])


class PyxoReboot(PyxoEntity, ButtonEntity):
    _attr_name = "Reboot"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry):
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_reboot"

    async def async_press(self):
        try:
            await self.matrix.reboot()
        except MatrixCommunicationError as err:
            raise HomeAssistantError(str(err)) from err
