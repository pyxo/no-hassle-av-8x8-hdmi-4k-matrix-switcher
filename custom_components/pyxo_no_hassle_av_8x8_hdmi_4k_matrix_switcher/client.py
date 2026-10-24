"""Small asynchronous, send-only No Hassle A/V UDP client (no HA imports)."""

import asyncio
import ipaddress
import socket
from contextlib import closing

OUTPUT_ADDRESSES = ("00", "01", "02", "03", "11", "12", "13", "14")
DEFAULT_PORT = 5000


class MatrixCommunicationError(Exception):
    """DNS, timeout, or local UDP delivery failure; remote delivery is unknown."""


def physical_number(value: int) -> int:
    """Require a physical input/output number, 1 through 8, excluding bool."""
    if type(value) is not int or not 1 <= value <= 8:
        raise ValueError("Physical input and output numbers must be integers from 1 to 8")
    return value


def route_command(output: int, input_number: int) -> bytes:
    """Encode physical port numbers without exposing broadcast addressing."""
    address = OUTPUT_ADDRESSES[physical_number(output) - 1]
    return f"@T {address} {physical_number(input_number) - 1:02d} !".encode("ascii")


def normalize_host(host: str) -> str:
    """Accept an IP literal or DNS hostname, never URLs or shell fragments."""
    if not isinstance(host, str):
        raise ValueError("Host must be a hostname or IP address")
    host = host.strip().rstrip(".")
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        pass
    try:
        host = host.encode("idna").decode("ascii").lower()
    except UnicodeError as err:
        raise ValueError("Invalid hostname") from err
    labels = host.split(".")
    if len(host) > 253 or any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label)
        for label in labels
    ):
        raise ValueError("Host must be a hostname or IP address without a port or URL")
    return host


def validate_port(port: int) -> int:
    """Validate a UDP port without silently coercing floats or booleans."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Port must be an integer from 1 to 65535")
    return port


class MatrixClient:
    """Resolve and send each command asynchronously; never poll or probe hardware."""

    def __init__(self, host: str, port: int = DEFAULT_PORT, *, timeout: float = 5.0):
        self.host = normalize_host(host)
        self.port = validate_port(port)
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not 0 < timeout <= 60
        ):
            raise ValueError("Timeout must be greater than zero and at most 60 seconds")
        self.timeout = timeout

    async def route(self, output: int, input_number: int) -> None:
        """Send exactly one route command; return does not confirm hardware state."""
        await self._send(route_command(output, input_number))

    async def reboot(self) -> None:
        """Send the documented reboot command, only when explicitly requested."""
        await self._send(b"@T 50 !")

    async def _send(self, command: bytes) -> None:
        loop = asyncio.get_running_loop()
        try:
            async with asyncio.timeout(self.timeout):
                addresses = await loop.getaddrinfo(
                    self.host,
                    self.port,
                    family=socket.AF_UNSPEC,
                    type=socket.SOCK_DGRAM,
                    proto=socket.IPPROTO_UDP,
                )
                if not addresses:
                    raise OSError("DNS returned no UDP addresses")
                # No automatic retries: delivery is unknowable and reboot is disruptive.
                family, kind, proto, _, address = addresses[0]
                with closing(socket.socket(family, kind, proto)) as udp:
                    udp.setblocking(False)
                    await loop.sock_sendto(udp, command, address)
        except (OSError, TimeoutError) as err:
            raise MatrixCommunicationError(
                f"Unable to send UDP command to {self.host}:{self.port}: {err}"
            ) from err
