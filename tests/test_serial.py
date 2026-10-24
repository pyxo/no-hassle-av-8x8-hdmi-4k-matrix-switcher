"""Mock the serial transport; no device ports are ever opened."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import serialx

from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.client import (
    MatrixCommunicationError,
)
from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.serial_client import (
    SerialMatrixClient,
    validate_serial_path,
)


@pytest.mark.parametrize("append_cr,tail", [(False, b""), (True, b"\r")])
async def test_serial_settings_bytes_and_close(append_cr, tail):
    serial = AsyncMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=serial)
    context.__aexit__ = AsyncMock(return_value=False)
    with patch("serialx.async_serial_for_url", return_value=context) as open_serial:
        client = SerialMatrixClient("/dev/ttyUSB0", append_cr=append_cr)
        await client.route(5, 8)
        serial.write.assert_awaited_once_with(b"@T 11 07 !" + tail)
        serial.flush.assert_awaited_once()
        open_serial.assert_called_once_with(
            "/dev/ttyUSB0",
            baudrate=115200,
            byte_size=8,
            parity=serialx.Parity.NONE,
            stopbits=serialx.StopBits.ONE,
        )
        context.__aexit__.assert_awaited_once()
        await client.reboot()
        assert serial.write.call_args.args == (b"@T 50 !" + tail,)


@pytest.mark.parametrize(
    "error",
    [
        OSError("port missing"),
        TimeoutError(),
        ValueError("invalid serial setting"),
        serialx.SerialException("transport failure"),
    ],
)
async def test_serial_failure(error):
    context = MagicMock()
    context.__aenter__ = AsyncMock(side_effect=error)
    with patch("serialx.async_serial_for_url", return_value=context):
        with pytest.raises(MatrixCommunicationError):
            await SerialMatrixClient("/dev/ttyUSB0").route(1, 1)


@pytest.mark.parametrize(
    "path", ["", "socket://host:5000", "esphome://host", "/tmp/file", "COM0", None]
)
def test_local_serial_path_only(path):
    with pytest.raises(ValueError):
        validate_serial_path(path)


async def test_cancelled_serial_write_closes_context():
    import asyncio

    serial = AsyncMock()
    serial.write.side_effect = asyncio.CancelledError
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=serial)
    context.__aexit__ = AsyncMock(return_value=False)
    with patch("serialx.async_serial_for_url", return_value=context):
        with pytest.raises(asyncio.CancelledError):
            await SerialMatrixClient("/dev/ttyUSB0").route(8, 8)
        context.__aexit__.assert_awaited_once()
