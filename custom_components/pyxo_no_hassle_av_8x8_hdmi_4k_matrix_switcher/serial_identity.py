"""Discover serial metadata and preserve OS-managed persistent device links."""

import os
from pathlib import Path

import serialx
from homeassistant.core import HomeAssistant

SERIAL_LINK_DIRS = (Path("/dev/serial/by-id"), Path("/dev/serial/by-path"))


def preferred_serial_path(path: str) -> str:
    """Prefer adapter identity, then USB location, without opening any serial port.

    Never dereference an already persistent configured link into a numbered port:
    the OS must resolve that link again when a command opens it after a reboot.
    """
    if any(path.startswith(f"{directory}/") for directory in SERIAL_LINK_DIRS):
        return path
    target = os.path.realpath(path)
    for directory in SERIAL_LINK_DIRS:
        try:
            links = sorted(directory.iterdir())
        except OSError:
            continue
        for link in links:
            if link.is_symlink() and os.path.realpath(link) == target:
                return str(link)
    return path


async def async_preferred_serial_path(hass: HomeAssistant, path: str) -> str:
    """Keep filesystem enumeration off Home Assistant's event loop."""
    return await hass.async_add_executor_job(preferred_serial_path, path)


async def async_serial_choices(hass: HomeAssistant) -> list[dict[str, str]]:
    """Enumerate ports for the UI without opening, writing, or probing devices."""
    try:
        ports = await serialx.async_list_serial_ports()
    except OSError:
        return []  # Manual paths remain available when enumeration is unsupported.
    choices = {}
    for port in ports:
        path = await async_preferred_serial_path(hass, str(port.device))
        description = port.product or "Serial port"
        if port.serial_number:
            description += f" ({port.serial_number})"
        choices[path] = {"value": path, "label": f"{description} — {path}"}
    return [choices[key] for key in sorted(choices)]
