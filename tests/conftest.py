"""Use real Home Assistant with all hardware communication replaced."""

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.const import DOMAIN
from custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.model import labels


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    with patch("serialx.async_list_serial_ports", new_callable=AsyncMock, return_value=[]):
        yield


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Matrix 1",
        data={
            "name": "Matrix 1",
            "connection": "udp",
            "host": "matrix.example",
            "port": 5000,
        },
        options=labels({}),
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def hardware():
    with (
        patch(
            "custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.client.MatrixClient.route",
            new_callable=AsyncMock,
        ) as route,
        patch(
            "custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.client.MatrixClient.reboot",
            new_callable=AsyncMock,
        ) as reboot,
        patch(
            "custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.serial_client.SerialMatrixClient.route",
            new_callable=AsyncMock,
        ) as serial_route,
        patch(
            "custom_components.pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher.serial_client.SerialMatrixClient.reboot",
            new_callable=AsyncMock,
        ) as serial_reboot,
    ):
        yield route, reboot, serial_route, serial_reboot
