"""Pyxo local No Hassle A/V matrix integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .client import MatrixClient
from .const import APPEND_CR, CONNECTION, PLATFORMS, SERIAL_PATH
from .model import MatrixRuntime
from .serial_client import SerialMatrixClient

type PyxoConfigEntry = ConfigEntry[MatrixRuntime]


async def async_setup_entry(hass: HomeAssistant, entry: PyxoConfigEntry) -> bool:
    """Create a send-only client without probing or changing hardware."""
    data = entry.data
    if data[CONNECTION] == "serial":
        client = SerialMatrixClient(data[SERIAL_PATH], append_cr=data.get(APPEND_CR, False))
    else:
        client = MatrixClient(data["host"], data["port"])
    entry.runtime_data = MatrixRuntime(client)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PyxoConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
