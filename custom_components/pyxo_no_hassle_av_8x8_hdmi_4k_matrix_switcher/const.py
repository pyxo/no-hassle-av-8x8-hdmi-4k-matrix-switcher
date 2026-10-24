"""Pyxo constants."""

from homeassistant.const import Platform

DOMAIN = "pyxo_no_hassle_av_8x8_hdmi_4k_matrix_switcher"
PLATFORMS = (Platform.SELECT, Platform.BUTTON)
CONNECTION = "connection"
SERIAL_PATH = "serial_path"
APPEND_CR = "append_cr"
SHOW_REBOOT = "show_reboot"
INPUT_KEYS = tuple(f"input_{i}" for i in range(1, 9))
OUTPUT_KEYS = tuple(f"output_{i}" for i in range(1, 9))
