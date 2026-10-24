"""Eight persistent, explicitly assumed routing selectors per matrix."""

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.restore_state import ExtraStoredData, RestoreEntity

from .client import MatrixCommunicationError
from .const import INPUT_KEYS, OUTPUT_KEYS
from .entity import PyxoEntity
from .model import labels

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(PyxoSelect(entry, output) for output in range(1, 9))


@dataclass
class RouteStoredData(ExtraStoredData):
    input_number: int | None

    def as_dict(self):
        return {"input_number": self.input_number}


class PyxoSelect(PyxoEntity, SelectEntity, RestoreEntity):
    _attr_assumed_state = True
    _attr_icon = "mdi:video-input-hdmi"

    def __init__(self, entry, output):
        super().__init__(entry)
        self.output = output
        config = labels(dict(entry.options))
        self._attr_name = config[OUTPUT_KEYS[output - 1]]
        self._attr_options = [config[key] for key in INPUT_KEYS]
        self._attr_unique_id = f"{entry.entry_id}_output_{output}"

    @property
    def current_option(self):
        input_number = self.matrix.inputs[self.output - 1]
        return self.options[input_number - 1] if input_number is not None else None

    @property
    def extra_state_attributes(self):
        return {
            "physical_output": self.output,
            "physical_input": self.matrix.inputs[self.output - 1],
            "state_source": self.matrix.sources[self.output - 1],
            "readback_supported": False,
        }

    @property
    def extra_restore_state_data(self):
        return RouteStoredData(self.matrix.inputs[self.output - 1])

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        previous = await self.async_get_last_extra_data()
        if previous is not None:
            value = previous.as_dict().get("input_number")
            if type(value) is int and 1 <= value <= 8:
                self.matrix.inputs[self.output - 1] = value
                self.matrix.sources[self.output - 1] = "restored"
        self.matrix.listeners.add(self.async_write_ha_state)
        self.async_on_remove(lambda: self.matrix.listeners.discard(self.async_write_ha_state))

    async def async_select_option(self, option):
        if option not in self.options:
            raise ServiceValidationError("Unknown input label")
        try:
            await self.matrix.route(self.output, self.options.index(option) + 1)
        except MatrixCommunicationError as err:
            raise HomeAssistantError(str(err)) from err
