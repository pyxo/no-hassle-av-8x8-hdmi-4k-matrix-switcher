"""Configuration validation and per-matrix optimistic state."""

import asyncio
from collections.abc import Callable
from contextlib import AsyncExitStack
from typing import Any

from .client import (
    MatrixClient,
    MatrixCommunicationError,
    normalize_host,
    physical_number,
    validate_port,
)
from .const import APPEND_CR, CONNECTION, INPUT_KEYS, OUTPUT_KEYS, SERIAL_PATH, SHOW_REBOOT
from .serial_client import SerialMatrixClient, validate_serial_path


def labels(values: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for keys, prefix in ((INPUT_KEYS, "Input"), (OUTPUT_KEYS, "Output")):
        for i, key in enumerate(keys, 1):
            value = values.get(key, f"{prefix} {i}")
            if not isinstance(value, str) or len(value.strip()) > 100:
                raise ValueError("Labels must contain 1–100 characters")
            result[key] = value.strip() or f"{prefix} {i}"
    if len({result[key].casefold() for key in INPUT_KEYS}) != 8:
        raise ValueError("Input labels must be unique within each matrix")
    result[SHOW_REBOOT] = values.get(SHOW_REBOOT, False)
    if type(result[SHOW_REBOOT]) is not bool:
        raise ValueError("Reboot option must be a boolean")
    return result


def connection_data(values: dict[str, Any]) -> dict[str, Any]:
    name = values.get("name", "")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        raise ValueError("Matrix name is required (1–100 characters)")
    result = {"name": name.strip(), CONNECTION: values.get(CONNECTION, "udp")}
    if result[CONNECTION] == "udp":
        result.update(
            host=normalize_host(values.get("host", "")),
            port=validate_port(values.get("port", 5000)),
        )
    elif result[CONNECTION] == "serial":
        result[SERIAL_PATH] = validate_serial_path(values.get(SERIAL_PATH, ""))
        result[APPEND_CR] = values.get(APPEND_CR, False)
        if type(result[APPEND_CR]) is not bool:
            raise ValueError("Carriage return option must be a boolean")
    else:
        raise ValueError("Unsupported connection type")
    return result


def endpoint(data: dict[str, Any]) -> tuple:
    if data[CONNECTION] == "serial":
        return ("serial", data[SERIAL_PATH])
    return ("udp", data["host"], data["port"])


class MatrixRuntime:
    """Serialize each output; last successful send is assumed, never confirmed."""

    def __init__(self, client: MatrixClient | SerialMatrixClient):
        self.client = client
        self.inputs: list[int | None] = [None] * 8
        self.sources = ["unknown"] * 8
        self.locks = [asyncio.Lock() for _ in range(8)]
        self.listeners: set[Callable[[], None]] = set()

    def notify(self):
        for listener in tuple(self.listeners):
            listener()

    async def route(self, output: int, input_number: int):
        physical_number(output)
        physical_number(input_number)
        async with self.locks[output - 1]:
            try:
                await self.client.route(output, input_number)
            except MatrixCommunicationError, asyncio.CancelledError:
                self.inputs[output - 1] = None
                self.sources[output - 1] = "unknown"
                self.notify()
                raise
            self.inputs[output - 1] = input_number
            self.sources[output - 1] = "last_command"
            self.notify()

    async def reboot(self):
        async with AsyncExitStack() as stack:
            for lock in self.locks:
                await stack.enter_async_context(lock)
            try:
                await self.client.reboot()
            finally:
                # Even a failed send may have reached the hardware.
                self.inputs[:] = [None] * 8
                self.sources[:] = ["unknown"] * 8
                self.notify()
