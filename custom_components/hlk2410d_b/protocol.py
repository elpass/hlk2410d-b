"""Protocol utilities for HLK-LD2410D-B BLE communication."""
from __future__ import annotations

import struct
import logging

from .const import (
    FRAME_HEADER,
    FRAME_FOOTER,
    CMD_ENABLE_CONFIG,
    CMD_END_CONFIG,
    CMD_READ_SENSOR_CONFIG,
    CMD_CONFIG_SENSOR_PARAM,
    CMD_AUTO_THRESHOLD_GEN,
    CMD_AUTO_THRESHOLD_PROGRESS,
    CMD_SAVE_PARAMS,
    CMD_RESTART_MODULE,
    CMD_SET_SENSITIVITY,
    CMD_READ_SENSITIVITY,
)

_LOGGER = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
#  Frame build / parse
# ────────────────────────────────────────────────────────────

def build_frame(cmd: int, payload: bytes = b"") -> bytes:
    """Build a complete protocol frame.

    Layout:  HEADER(4) | LENGTH(2 LE) | CMD(2 LE) | PAYLOAD(n) | FOOTER(4)
    LENGTH = 2 (cmd bytes) + len(payload)
    """
    length = 2 + len(payload)
    frame = (
        FRAME_HEADER
        + struct.pack("<H", length)
        + struct.pack("<H", cmd)
        + payload
        + FRAME_FOOTER
    )
    _LOGGER.debug(
        "TX cmd=0x%04X len=%d payload=%s → %s",
        cmd, length, payload.hex() if payload else "-", frame.hex(),
    )
    return frame


def parse_frame(data: bytes) -> tuple[int, bytes] | None:
    """Parse a frame → (cmd, payload) or None."""
    if len(data) < 10:
        return None
    if data[:4] != FRAME_HEADER:
        _LOGGER.debug("Bad header: %s", data[:4].hex())
        return None
    if data[-4:] != FRAME_FOOTER:
        _LOGGER.debug("Bad footer: %s", data[-4:].hex())
        return None
    length = struct.unpack_from("<H", data, 4)[0]
    cmd = struct.unpack_from("<H", data, 6)[0]
    payload = data[8:-4]
    _LOGGER.debug(
        "RX cmd=0x%04X len=%d payload=%s",
        cmd, length, payload.hex() if payload else "-",
    )
    return cmd, payload


# ────────────────────────────────────────────────────────────
#  ACK helpers
# ────────────────────────────────────────────────────────────

def is_ack(cmd: int) -> bool:
    """ACK has bit 8 set."""
    return bool(cmd & 0x0100)


def get_ack_cmd(cmd: int) -> int:
    """Expected ACK command word."""
    return cmd | 0x0100


def check_ack_status(payload: bytes) -> bool:
    """True when first two payload bytes (status word) == 0x0000."""
    if len(payload) < 2:
        return True          # no status field → assume OK
    return struct.unpack_from("<H", payload, 0)[0] == 0


# ────────────────────────────────────────────────────────────
#  Command builders
# ────────────────────────────────────────────────────────────

def build_enable_config() -> bytes:
    """1.2.1 Enable config mode."""
    return build_frame(CMD_ENABLE_CONFIG, struct.pack("<H", 1))


def build_end_config() -> bytes:
    """1.2.2 End config mode."""
    return build_frame(CMD_END_CONFIG)


def build_read_sensor_param(param_id: int) -> bytes:
    """1.2.5 Read a sensor parameter."""
    return build_frame(CMD_READ_SENSOR_CONFIG, struct.pack("<H", param_id))


def build_config_sensor_param(param_id: int, value: int) -> bytes:
    """1.2.6 Set a sensor parameter (param_id LE16 + value LE32)."""
    return build_frame(CMD_CONFIG_SENSOR_PARAM, struct.pack("<HI", param_id, value))


def build_auto_threshold_gen(gate_coeff_value: int) -> bytes:
    """1.2.8 Start auto-threshold generation.

    gate_coeff_value is one of 1, 5, 10, 15, 20.
    Three uint16 LE = coeff * 10.
    """
    v = gate_coeff_value * 10
    return build_frame(CMD_AUTO_THRESHOLD_GEN, struct.pack("<HHH", v, v, v))


def build_auto_threshold_progress() -> bytes:
    """1.2.9 Query auto-threshold progress."""
    return build_frame(CMD_AUTO_THRESHOLD_PROGRESS)


def build_save_params() -> bytes:
    """1.2.11 Save parameters."""
    return build_frame(CMD_SAVE_PARAMS)


def build_restart_module() -> bytes:
    """1.2.14 Restart module."""
    return build_frame(CMD_RESTART_MODULE)


def build_set_sensitivity(level: int) -> bytes:
    """1.2.17 Set sensitivity (1-5)."""
    return build_frame(CMD_SET_SENSITIVITY, struct.pack("<H", level))


def build_read_sensitivity() -> bytes:
    """1.2.18 Read sensitivity."""
    return build_frame(CMD_READ_SENSITIVITY)


# ────────────────────────────────────────────────────────────
#  Response parsers
# ────────────────────────────────────────────────────────────

def parse_read_sensor_param_response(
    cmd: int, payload: bytes, param_id: int
) -> int | None:
    """Parse ACK for read_sensor_config → value or None."""
    if cmd != get_ack_cmd(CMD_READ_SENSOR_CONFIG):
        return None
    if len(payload) < 8:
        return None
    status, resp_pid = struct.unpack_from("<HH", payload, 0)
    if status != 0 or resp_pid != param_id:
        _LOGGER.warning("Read param err: st=%d pid=0x%04X", status, resp_pid)
        return None
    return struct.unpack_from("<I", payload, 4)[0]


def parse_read_sensitivity_response(cmd: int, payload: bytes) -> int | None:
    """Parse ACK for read_sensitivity → level (1-5) or None."""
    if cmd != get_ack_cmd(CMD_READ_SENSITIVITY):
        return None
    if len(payload) < 4:
        return None
    status = struct.unpack_from("<H", payload, 0)[0]
    if status != 0:
        return None
    return struct.unpack_from("<H", payload, 2)[0]


def parse_auto_threshold_progress_response(
    cmd: int, payload: bytes
) -> int | None:
    """Parse ACK for threshold-progress → 0-100 or None."""
    if cmd != get_ack_cmd(CMD_AUTO_THRESHOLD_PROGRESS):
        return None
    if len(payload) < 4:
        return None
    status = struct.unpack_from("<H", payload, 0)[0]
    if status != 0:
        return None
    return struct.unpack_from("<H", payload, 2)[0]


def parse_distance_text(data: bytes) -> str | None:
    """Parse 'distance:XXX' or 'OFF' from normal-mode notification."""
    try:
        text = data.decode("ascii", errors="ignore").strip()
    except Exception:
        return None
    if text == "OFF" or text.startswith("distance:"):
        return text
    return None