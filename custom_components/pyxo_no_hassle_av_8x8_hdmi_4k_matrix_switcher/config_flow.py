"""UI setup, label options and transport reconfiguration without device probes."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import APPEND_CR, CONNECTION, DOMAIN, INPUT_KEYS, OUTPUT_KEYS, SERIAL_PATH, SHOW_REBOOT
from .model import connection_data, endpoint, labels
from .serial_identity import async_preferred_serial_path, async_serial_choices


def connection_schema(values: dict[str, Any], serial_choices: list[dict[str, str]]) -> vol.Schema:
    """Both connection fields remain visible so transport can be changed later."""
    return vol.Schema(
        {
            vol.Required("name", default=values.get("name", "8x8 HDMI 4K Matrix Switcher")): str,
            vol.Required(CONNECTION, default=values.get(CONNECTION, "udp")): vol.In(
                ["udp", "serial"]
            ),
            vol.Optional("host", default=values.get("host", "")): str,
            vol.Optional("port", default=values.get("port", 5000)): vol.All(
                int, vol.Range(min=1, max=65535)
            ),
            vol.Optional(SERIAL_PATH, default=values.get(SERIAL_PATH, "")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=serial_choices,
                    custom_value=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(APPEND_CR, default=values.get(APPEND_CR, False)): bool,
        }
    )


def labels_schema(values: dict[str, Any]) -> vol.Schema:
    fields = {}
    for keys, prefix in ((INPUT_KEYS, "Input"), (OUTPUT_KEYS, "Output")):
        for i, key in enumerate(keys, 1):
            fields[vol.Required(key, default=values.get(key, f"{prefix} {i}"))] = str
    fields[vol.Required(SHOW_REBOOT, default=values.get(SHOW_REBOOT, False))] = bool
    return vol.Schema(fields)


class PyxoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PyxoOptionsFlow()

    async def _async_connection_data(self, user_input):
        data = connection_data(user_input)
        if data[CONNECTION] == "serial":
            data[SERIAL_PATH] = await async_preferred_serial_path(self.hass, data[SERIAL_PATH])
        return data

    async def _async_connection_schema(self, values):
        choices = await async_serial_choices(self.hass)
        current = values.get(SERIAL_PATH)
        if current and current not in {choice["value"] for choice in choices}:
            choices.append({"value": current, "label": current})
        return connection_schema(values, choices)

    def _duplicate(self, data, exclude=None):
        return any(
            entry.entry_id != exclude and endpoint(dict(entry.data)) == endpoint(data)
            for entry in self._async_current_entries()
        )

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                data = await self._async_connection_data(user_input)
            except ValueError:
                errors["base"] = "invalid_connection"
            else:
                if self._duplicate(data):
                    return self.async_abort(reason="already_configured")
                self._connection_data = data
                return await self.async_step_labels()
        return self.async_show_form(
            step_id="user",
            data_schema=await self._async_connection_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_labels(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                options = labels(user_input)
            except ValueError:
                errors["base"] = "invalid_labels"
            else:
                # No serial number/readback exists. Entry ID is the stable local identity.
                # Check again in case another setup completed while this form was open.
                if self._duplicate(self._connection_data):
                    return self.async_abort(reason="already_configured")
                return self.async_create_entry(
                    title=self._connection_data["name"], data=self._connection_data, options=options
                )
        return self.async_show_form(
            step_id="labels", data_schema=labels_schema(user_input or {}), errors=errors
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            try:
                data = await self._async_connection_data(user_input)
            except ValueError:
                errors["base"] = "invalid_connection"
            else:
                if self._duplicate(data, entry.entry_id):
                    errors["base"] = "already_configured"
                else:
                    return self.async_update_reload_and_abort(entry, title=data["name"], data=data)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=await self._async_connection_schema(user_input or dict(entry.data)),
            errors=errors,
        )


class PyxoOptionsFlow(config_entries.OptionsFlowWithReload):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                options = labels(user_input)
            except ValueError:
                errors["base"] = "invalid_labels"
            else:
                return self.async_create_entry(title="", data=options)
        return self.async_show_form(
            step_id="init",
            data_schema=labels_schema(user_input or dict(self.config_entry.options)),
            errors=errors,
        )
