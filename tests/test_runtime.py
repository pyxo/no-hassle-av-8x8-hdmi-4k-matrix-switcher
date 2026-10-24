"""Operation ordering matters more than implementation-shaped unit tests."""

import asyncio
from unittest.mock import AsyncMock

from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.model import MatrixRuntime


async def test_same_output_serialized_other_output_independent():
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    calls = []

    async def send(output, input_number):
        calls.append((output, input_number))
        if (output, input_number) == (1, 1):
            first_started.set()
            await release_first.wait()

    client = AsyncMock()
    client.route.side_effect = send
    matrix = MatrixRuntime(client)
    first = asyncio.create_task(matrix.route(1, 1))
    await first_started.wait()
    second = asyncio.create_task(matrix.route(1, 2))
    await matrix.route(2, 8)
    assert calls == [(1, 1), (2, 8)]
    release_first.set()
    await asyncio.gather(first, second)
    assert calls == [(1, 1), (2, 8), (1, 2)]
    assert matrix.inputs[:2] == [2, 8]


async def test_reboot_waits_for_routes_and_invalidates():
    started = asyncio.Event()
    release = asyncio.Event()

    async def send(*args):
        started.set()
        await release.wait()

    client = AsyncMock()
    client.route.side_effect = send
    matrix = MatrixRuntime(client)
    route = asyncio.create_task(matrix.route(1, 8))
    await started.wait()
    reboot = asyncio.create_task(matrix.reboot())
    await asyncio.sleep(0)
    client.reboot.assert_not_awaited()
    release.set()
    await asyncio.gather(route, reboot)
    client.reboot.assert_awaited_once()
    assert matrix.inputs == [None] * 8
