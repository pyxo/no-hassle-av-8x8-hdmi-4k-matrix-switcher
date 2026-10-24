"""Asynchronous local RS232 transport for the documented matrix protocol."""

import asyncio
import posixpath
import re

import serialx

from .client import MatrixCommunicationError, route_command


def validate_serial_path(path: str) -> str:
    """Limit MVP serial connections to local device paths (no remote proxies)."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("A local serial device path is required")
    path = path.strip()
    if path.startswith("/dev/"):
        path = posixpath.normpath(path)
    if not (path.startswith("/dev/") or re.fullmatch(r"COM[1-9][0-9]*", path, re.IGNORECASE)):
        raise ValueError("Use a local /dev/... device path or COM port")
    if any(c.isspace() or ord(c) < 32 for c in path):
        raise ValueError("Invalid serial device path")
    return path.upper() if path.upper().startswith("COM") else path


class SerialMatrixClient:
    """Send the same documented ASCII protocol over local RS232 at 115200 8N1."""

    def __init__(self, path: str, *, append_cr: bool = False):
        self.path = validate_serial_path(path)
        if type(append_cr) is not bool:
            raise ValueError("Carriage return option must be a boolean")
        self.append_cr = append_cr
        self._lock = asyncio.Lock()

    async def route(self, output: int, input_number: int) -> None:
        await self._send(route_command(output, input_number))

    async def reboot(self) -> None:
        await self._send(b"@T 50 !")

    async def _send(self, command: bytes) -> None:
        async with self._lock:
            try:
                async with asyncio.timeout(5):
                    async with serialx.async_serial_for_url(
                        self.path,
                        baudrate=115200,
                        byte_size=8,
                        parity=serialx.Parity.NONE,
                        stopbits=serialx.StopBits.ONE,
                    ) as serial:
                        await serial.write(command + (b"\r" if self.append_cr else b""))
                        await serial.flush()
            except (OSError, TimeoutError, ValueError, serialx.SerialException) as err:
                raise MatrixCommunicationError(f"Unable to send serial command: {err}") from err
