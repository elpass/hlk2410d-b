"""BLE connection manager for HLK-LD2410D-B."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    NOTIFY_UUID,
    WRITE_UUID,
    BLE_COMMAND_TIMEOUT,
    MODE_NORMAL,
    MODE_CONFIG,
)
from .protocol import (
    parse_frame,
    get_ack_cmd,
    check_ack_status,
    parse_distance_text,
    FRAME_HEADER,
    FRAME_FOOTER,
)

_LOGGER = logging.getLogger(__name__)


class BLEManager:
    """Manage BLE connection and notification routing."""

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        self._hass = hass
        self._address = address
        self._name = name
        self._client: BleakClient | None = None
        self._connected = False
        self._mode = MODE_NORMAL
        self._progress = 0
        self._lock = asyncio.Lock()

        self._buffer = bytearray()
        self._response_event = asyncio.Event()
        self._last_response: tuple[int, bytes] | None = None

        self._distance_cb: Callable[[str], None] | None = None
        self._disconnect_cb: Callable[[], None] | None = None

    # ── properties ──────────────────────────────────────────

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str) -> None:
        self._mode = value

    @property
    def progress(self) -> int:
        return self._progress

    @progress.setter
    def progress(self, value: int) -> None:
        self._progress = max(0, min(100, value))

    def set_distance_callback(self, cb: Callable[[str], None]) -> None:
        self._distance_cb = cb

    def set_disconnect_callback(self, cb: Callable[[], None]) -> None:
        self._disconnect_cb = cb

    # ── connection ──────────────────────────────────────────

    def _get_ble_device(self) -> BLEDevice | None:
        return bluetooth.async_ble_device_from_address(
            self._hass, self._address, connectable=True
        )

    async def connect(self) -> bool:
        async with self._lock:
            return await self._do_connect()

    async def _do_connect(self) -> bool:
        if self._client and self._client.is_connected:
            self._connected = True
            return True

        device = self._get_ble_device()
        if not device:
            _LOGGER.error("BLE device %s not found via HA bluetooth", self._address)
            return False

        try:
            self._client = await establish_connection(
                BleakClient,
                device,
                self._name,
                disconnected_callback=self._on_disconnect,
                max_attempts=3,
            )
            self._connected = True
            await self._client.start_notify(NOTIFY_UUID, self._on_notify)
            _LOGGER.info("Connected to %s (%s)", self._name, self._address)
            return True
        except Exception as err:
            _LOGGER.error("Connect failed for %s: %s", self._address, err)
            self._connected = False
            return False

    def _on_disconnect(self, _client: BleakClient) -> None:
        _LOGGER.warning("Disconnected from %s", self._address)
        self._connected = False
        self._client = None
        if self._disconnect_cb:
            self._hass.loop.call_soon_threadsafe(self._disconnect_cb)

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.stop_notify(NOTIFY_UUID)
            except Exception:
                pass
            try:
                await self._client.disconnect()
            except Exception:
                pass
        self._connected = False
        self._client = None

    async def ensure_connected(self) -> bool:
        if self._connected and self._client and self._client.is_connected:
            return True
        async with self._lock:
            return await self._do_connect()

    # ── notification handling ───────────────────────────────

    def _on_notify(self, _sender: int, data: bytearray) -> None:
        _LOGGER.debug("Notify %s: %s", self._address, data.hex())

        if self._mode == MODE_NORMAL:
            text = parse_distance_text(bytes(data))
            if text and self._distance_cb:
                self._hass.loop.call_soon_threadsafe(self._distance_cb, text)
            return

        self._buffer.extend(data)
        self._try_parse()

    def _try_parse(self) -> None:
        buf = bytes(self._buffer)
        hdr_pos = buf.find(FRAME_HEADER)
        if hdr_pos < 0:
            if len(self._buffer) > 512:
                self._buffer.clear()
            return
        if hdr_pos > 0:
            del self._buffer[:hdr_pos]
            buf = bytes(self._buffer)

        ftr_pos = buf.find(FRAME_FOOTER, 4)
        if ftr_pos < 0:
            return

        end = ftr_pos + len(FRAME_FOOTER)
        frame = buf[:end]
        del self._buffer[:end]

        result = parse_frame(frame)
        if result:
            self._last_response = result
            self._response_event.set()

        if len(self._buffer) >= 10:
            self._try_parse()

    # ── command I/O ─────────────────────────────────────────

    async def send_command(self, data: bytes) -> bool:
        """Raw write to WRITE_UUID (fire-and-forget)."""
        if not self._connected or not self._client:
            _LOGGER.error("Cannot send: not connected")
            return False
        try:
            await self._client.write_gatt_char(WRITE_UUID, data, response=False)
            _LOGGER.debug("Sent %d bytes to %s", len(data), self._address)
            return True
        except Exception as err:
            _LOGGER.error("Write failed: %s", err)
            return False

    async def send_and_wait_ack(
        self, cmd: int, data: bytes, timeout: float = BLE_COMMAND_TIMEOUT
    ) -> tuple[int, bytes] | None:
        self._response_event.clear()
        self._last_response = None
        self._buffer.clear()

        if not await self.send_command(data):
            return None

        expected = get_ack_cmd(cmd)
        try:
            await asyncio.wait_for(self._response_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout waiting ACK for cmd 0x%04X", cmd)
            return None

        if self._last_response:
            resp_cmd, resp_payload = self._last_response
            if resp_cmd == expected:
                return resp_cmd, resp_payload
            _LOGGER.warning("Expected ACK 0x%04X got 0x%04X", expected, resp_cmd)
        return None

    async def send_and_verify_ack(
        self, cmd: int, data: bytes, timeout: float = BLE_COMMAND_TIMEOUT
    ) -> bool:
        result = await self.send_and_wait_ack(cmd, data, timeout)
        if result is None:
            return False
        return check_ack_status(result[1])
