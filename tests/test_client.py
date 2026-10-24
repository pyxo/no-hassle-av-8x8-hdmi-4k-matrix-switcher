"""Offline protocol and UDP tests: no live sockets or matrices."""

import asyncio
import importlib.util
import socket
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Load the independent client without importing the HA integration package.
spec = importlib.util.spec_from_file_location(
    "pyxo_client",
    Path(__file__).parents[1]
    / "custom_components/pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher/client.py",
)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


@pytest.mark.parametrize(
    "output,address", enumerate(("00", "01", "02", "03", "11", "12", "13", "14"), 1)
)
@pytest.mark.parametrize("input_number", range(1, 9))
def test_all_64_routes(output, address, input_number):
    command = client.route_command(output, input_number)
    assert command == f"@T {address} {input_number - 1:02d} !".encode("ascii")
    assert command.split()[1] != b"04"
    assert not command.endswith((b"\r", b"\n"))


@pytest.mark.parametrize("invalid", [0, -1, 9, 4.0, "5", True, None])
def test_invalid_port_numbers(invalid):
    with pytest.raises(ValueError):
        client.route_command(invalid, 1)
    with pytest.raises(ValueError):
        client.route_command(1, invalid)


@pytest.mark.parametrize(
    "host", ["", "http://matrix", "matrix:5000", "a b", "a\n!", "a..b", "-matrix", "a" * 64]
)
def test_invalid_host(host):
    with pytest.raises(ValueError):
        client.MatrixClient(host)


@pytest.mark.parametrize("port", [0, 65536, True, 5000.0, "5000"])
def test_invalid_udp_port(port):
    with pytest.raises(ValueError):
        client.MatrixClient("matrix", port)


def test_host_normalization():
    assert client.normalize_host(" Matrix.EXAMPLE. ") == "matrix.example"
    assert client.normalize_host("2001:0db8::1") == "2001:db8::1"


@pytest.fixture
async def udp():
    loop = asyncio.get_running_loop()
    udp_socket = MagicMock()
    with (
        patch.object(
            loop,
            "getaddrinfo",
            AsyncMock(
                return_value=[
                    (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("192.0.2.1", 5000))
                ]
            ),
        ) as resolve,
        patch.object(loop, "sock_sendto", AsyncMock()) as send,
        patch.object(client.socket, "socket", return_value=udp_socket),
    ):
        yield resolve, send, udp_socket


async def test_udp_send_and_reboot(udp):
    resolve, send, sock = udp
    matrix = client.MatrixClient("matrix.example")
    await matrix.route(5, 8)
    send.assert_awaited_once_with(sock, b"@T 11 07 !", ("192.0.2.1", 5000))
    sock.setblocking.assert_called_once_with(False)
    sock.close.assert_called_once()
    resolve.assert_awaited_once_with(
        "matrix.example",
        5000,
        family=socket.AF_UNSPEC,
        type=socket.SOCK_DGRAM,
        proto=socket.IPPROTO_UDP,
    )
    await matrix.reboot()
    assert send.call_args.args[1] == b"@T 50 !"


@pytest.mark.parametrize(
    "stage,error",
    [
        ("dns", socket.gaierror("missing")),
        ("send", OSError("network unreachable")),
        ("send", TimeoutError()),
        ("empty", None),
    ],
)
async def test_failures(udp, stage, error):
    resolve, send, sock = udp
    if stage == "dns":
        resolve.side_effect = error
    elif stage == "empty":
        resolve.return_value = []
    else:
        send.side_effect = error
    with pytest.raises(client.MatrixCommunicationError):
        await client.MatrixClient("matrix").route(8, 1)
    if stage == "send":
        sock.close.assert_called_once()


async def test_cancellation_closes_socket(udp):
    _, send, sock = udp
    send.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await client.MatrixClient("matrix").route(1, 1)
    sock.close.assert_called_once()


async def test_invalid_route_sends_nothing(udp):
    resolve, send, _ = udp
    with pytest.raises(ValueError):
        await client.MatrixClient("matrix").route(0, 1)
    resolve.assert_not_awaited()
    send.assert_not_awaited()


async def test_ipv6_udp_destination(udp):
    resolve, send, sock = udp
    address = ("2001:db8::1", 5001, 0, 0)
    resolve.return_value = [(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", address)]
    await client.MatrixClient("2001:db8::1", 5001).route(8, 8)
    send.assert_awaited_once_with(sock, b"@T 14 07 !", address)


async def test_actual_dns_timeout(udp):
    resolve, send, _ = udp

    async def slow_dns(*args, **kwargs):
        await asyncio.Event().wait()

    resolve.side_effect = slow_dns
    with pytest.raises(client.MatrixCommunicationError):
        await client.MatrixClient("matrix", timeout=0.01).route(1, 1)
    send.assert_not_awaited()
