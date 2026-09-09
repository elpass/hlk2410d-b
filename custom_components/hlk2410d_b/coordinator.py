"""Data coordinator for HLK-LD2410D-B."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    DEFAULT_MAX_DISTANCE_M,
    DEFAULT_TARGET_DELAY_S,
    DEFAULT_SENSITIVITY,
    DEFAULT_GATE_COEFF,
    GATE_COEFF_MAP,
    MAX_DISTANCE_MIN_RAW,
    MAX_DISTANCE_MAX_RAW,
    MODE_NORMAL,
    MODE_CONFIG,
    PARAM_MAX_DISTANCE,
    PARAM_TARGET_DELAY,
    AUTO_THRESHOLD_POLL_INTERVAL,
)
from .ble_manager import BLEManager
from .protocol import (
    build_enable_config,
    build_end_config,
    build_read_sensor_param,
    build_config_sensor_param,
    build_auto_threshold_gen,
    build_auto_threshold_progress,
    build_save_params,
    build_restart_module,
    build_set_sensitivity,
    build_read_sensitivity,
    parse_read_sensor_param_response,
    parse_read_sensitivity_response,
    parse_auto_threshold_progress_response,
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
    check_ack_status,
)

_LOGGER = logging.getLogger(__name__)

# 特殊距离常量
DISTANCE_NO_TARGET = 2026   # 无目标时的返回值
DISTANCE_CONFIG_MODE = 0    # 配置模式时的返回值


class HLK2410DCoordinator:
    """Coordinate BLE operations for one HLK-LD2410D-B device."""

    def __init__(
        self, hass: HomeAssistant, ble: BLEManager, entry_id: str
    ) -> None:
        self.hass = hass
        self.ble = ble
        self.entry_id = entry_id
        self._op_lock = asyncio.Lock()

        # ── Confirmed module values (last read/written) ──
        self._mod_dist_m: float = DEFAULT_MAX_DISTANCE_M
        self._mod_delay_s: int = DEFAULT_TARGET_DELAY_S
        self._mod_sens: int = DEFAULT_SENSITIVITY
        self._mod_gate: int = DEFAULT_GATE_COEFF

        # ── Pending values (user-adjusted in UI) ──
        self._pend_dist_m: float = DEFAULT_MAX_DISTANCE_M
        self._pend_delay_s: int = DEFAULT_TARGET_DELAY_S
        self._pend_sens: int = DEFAULT_SENSITIVITY
        self._pend_gate: int = DEFAULT_GATE_COEFF

        # ── Sensor / diagnostic state ──
        self.distance_cm: int = DISTANCE_NO_TARGET  # 整型，单位厘米
        self.mode: str = MODE_NORMAL
        self.progress: int = 0

        # Wire BLE callbacks
        self.ble.set_distance_callback(self._on_distance)
        self.ble.set_disconnect_callback(self._on_disconnect)

    # ── signal helpers ──────────────────────────────────────

    def _sig(self, s: str) -> str:
        return f"{DOMAIN}_{s}_{self.entry_id}"

    def _notify(self, s: str) -> None:
        async_dispatcher_send(self.hass, self._sig(s))

    # ── BLE event callbacks ─────────────────────────────────

    @callback
    def _on_distance(self, text: str) -> None:
        """Parse distance notification → integer cm.

        - "distance:124" → 124
        - "OFF"          → 2026
        - config mode    → ignored (stays at current value; sensor shows 0)
        """
        if self.ble.mode != MODE_NORMAL:
            return

        if text == "OFF":
            self.distance_cm = DISTANCE_NO_TARGET
        elif text.startswith("distance:"):
            try:
                self.distance_cm = int(text.split(":")[1])
            except (ValueError, IndexError):
                _LOGGER.warning("Unparseable distance text: %s", text)
                self.distance_cm = DISTANCE_NO_TARGET
        else:
            _LOGGER.warning("Unknown distance format: %s", text)
            self.distance_cm = DISTANCE_NO_TARGET

        self._notify("distance")

    @callback
    def _on_disconnect(self) -> None:
        if self.mode == MODE_NORMAL:
            self.progress = 0
            self.ble.mode = MODE_NORMAL
            self.ble.progress = 0
            self._notify("diagnostic")

    # ── diagnostic state ────────────────────────────────────

    def _set_diag(self, mode: str, prog: int) -> None:
        self.mode = mode
        self.progress = prog
        self.ble.mode = mode
        self.ble.progress = prog
        self._notify("diagnostic")
        # 模式切换时也通知距离传感器刷新（配置模式→0，正常模式→恢复实时值）
        self._notify("distance")

    # ── config-mode transitions ─────────────────────────────

    async def _enter_config(self) -> bool:
        self._set_diag(MODE_CONFIG, 10)
        if not await self.ble.send_and_verify_ack(
            CMD_ENABLE_CONFIG, build_enable_config()
        ):
            _LOGGER.error("Enter config mode failed")
            self._set_diag(MODE_NORMAL, 0)
            return False
        return True

    async def _exit_config(self) -> bool:
        result = await self.ble.send_and_wait_ack(
            CMD_END_CONFIG, build_end_config()
        )
        if result is None or not check_ack_status(result[1]):
            _LOGGER.error("Exit config mode failed")
            return False
        self._set_diag(MODE_NORMAL, 100)
        self.hass.loop.call_later(1.0, self._set_diag, MODE_NORMAL, 0)
        return True

    # ════════════════════════════════════════════════════════
    #  READ
    # ════════════════════════════════════════════════════════

    async def read_parameters(self) -> bool:
        async with self._op_lock:
            if not await self.ble.ensure_connected():
                return False
            if not await self._enter_config():
                return False

            try:
                r = await self.ble.send_and_wait_ack(
                    CMD_READ_SENSOR_CONFIG,
                    build_read_sensor_param(PARAM_MAX_DISTANCE),
                )
                if r:
                    v = parse_read_sensor_param_response(
                        r[0], r[1], PARAM_MAX_DISTANCE
                    )
                    if v is not None:
                        d = v / 10.0
                        self._mod_dist_m = d
                        self._pend_dist_m = d
                        _LOGGER.info("Read max_dist: %d → %.1f m", v, d)
                self._set_diag(MODE_CONFIG, 30)

                r = await self.ble.send_and_wait_ack(
                    CMD_READ_SENSOR_CONFIG,
                    build_read_sensor_param(PARAM_TARGET_DELAY),
                )
                if r:
                    v = parse_read_sensor_param_response(
                        r[0], r[1], PARAM_TARGET_DELAY
                    )
                    if v is not None:
                        self._mod_delay_s = v
                        self._pend_delay_s = v
                        _LOGGER.info("Read delay: %d s", v)
                self._set_diag(MODE_CONFIG, 60)

                r = await self.ble.send_and_wait_ack(
                    CMD_READ_SENSITIVITY, build_read_sensitivity()
                )
                if r:
                    v = parse_read_sensitivity_response(r[0], r[1])
                    if v is not None and 1 <= v <= 5:
                        self._mod_sens = v
                        self._pend_sens = v
                        _LOGGER.info("Read sens: %d", v)
                self._set_diag(MODE_CONFIG, 90)

                self._notify("params")
                return await self._exit_config()

            except Exception as exc:
                _LOGGER.error("Read error: %s", exc)
                await self._exit_config()
                return False

    # ════════════════════════════════════════════════════════
    #  SET
    # ════════════════════════════════════════════════════════

    async def set_parameters(self) -> tuple[bool, str]:
        async with self._op_lock:
            changes: dict[str, Any] = {}
            if self._pend_dist_m != self._mod_dist_m:
                changes["dist"] = self._pend_dist_m
            if self._pend_delay_s != self._mod_delay_s:
                changes["delay"] = self._pend_delay_s
            if self._pend_sens != self._mod_sens:
                changes["sens"] = self._pend_sens
            if self._pend_gate != self._mod_gate:
                changes["gate"] = self._pend_gate

            if not changes:
                return False, "参数无变化不执行"

            if not await self.ble.ensure_connected():
                return False, "连接失败"
            if not await self._enter_config():
                return False, "进入配置模式失败"

            prog = 10
            try:
                if "dist" in changes:
                    prog = 20
                    self._set_diag(MODE_CONFIG, prog)
                    raw = int(changes["dist"] * 10)
                    raw = max(MAX_DISTANCE_MIN_RAW, min(MAX_DISTANCE_MAX_RAW, raw))
                    if not await self.ble.send_and_verify_ack(
                        CMD_CONFIG_SENSOR_PARAM,
                        build_config_sensor_param(PARAM_MAX_DISTANCE, raw),
                    ):
                        await self._exit_config()
                        return False, "设置最大距离失败"
                    self._mod_dist_m = raw / 10.0

                if "delay" in changes:
                    prog = 30
                    self._set_diag(MODE_CONFIG, prog)
                    if not await self.ble.send_and_verify_ack(
                        CMD_CONFIG_SENSOR_PARAM,
                        build_config_sensor_param(PARAM_TARGET_DELAY, changes["delay"]),
                    ):
                        await self._exit_config()
                        return False, "设置延迟失败"
                    self._mod_delay_s = changes["delay"]

                if "gate" in changes:
                    prog = 40
                    self._set_diag(MODE_CONFIG, prog)
                    cv = GATE_COEFF_MAP[changes["gate"]]
                    if not await self.ble.send_and_verify_ack(
                        CMD_AUTO_THRESHOLD_GEN, build_auto_threshold_gen(cv),
                    ):
                        await self._exit_config()
                        return False, "启动门限生成失败"

                    while prog < 80:
                        await asyncio.sleep(AUTO_THRESHOLD_POLL_INTERVAL)
                        r = await self.ble.send_and_wait_ack(
                            CMD_AUTO_THRESHOLD_PROGRESS,
                            build_auto_threshold_progress(),
                        )
                        if r:
                            dp = parse_auto_threshold_progress_response(r[0], r[1])
                            if dp is not None:
                                if dp >= 100:
                                    prog = 80
                                    break
                                if dp >= 50:
                                    mp = int(dp * 0.8)
                                    if mp > prog:
                                        prog = mp
                                        self._set_diag(MODE_CONFIG, prog)

                    self._mod_gate = changes["gate"]

                if "sens" in changes:
                    prog = 90
                    self._set_diag(MODE_CONFIG, prog)
                    if not await self.ble.send_and_verify_ack(
                        CMD_SET_SENSITIVITY, build_set_sensitivity(changes["sens"]),
                    ):
                        await self._exit_config()
                        return False, "设置灵敏度失败"
                    self._mod_sens = changes["sens"]

                await self.ble.send_and_verify_ack(CMD_SAVE_PARAMS, build_save_params())

                self._pend_dist_m = self._mod_dist_m
                self._pend_delay_s = self._mod_delay_s
                self._pend_sens = self._mod_sens
                self._pend_gate = self._mod_gate

                self._notify("params")
                await self._exit_config()
                return True, "设置成功"

            except Exception as exc:
                _LOGGER.error("Set error: %s", exc)
                await self._exit_config()
                return False, f"设置异常: {exc}"

    # ════════════════════════════════════════════════════════
    #  RESTART
    # ════════════════════════════════════════════════════════

    async def restart_module(self) -> bool:
        async with self._op_lock:
            if not await self.ble.ensure_connected():
                return False
            if not await self._enter_config():
                return False

            data = build_restart_module()
            sent = await self.ble.send_command(data)
            if not sent:
                _LOGGER.error("Failed to send restart command")
                self._set_diag(MODE_NORMAL, 0)
                return False

            _LOGGER.info("Restart command sent, entering countdown")
            self._set_diag(MODE_CONFIG, 20)

            for pct in range(30, 101, 10):
                await asyncio.sleep(1.0)
                self._set_diag(MODE_CONFIG, pct)

            _LOGGER.info("Reconnecting after module restart...")
            reconnected = await self.ble.ensure_connected()
            if not reconnected:
                _LOGGER.warning("Reconnect failed after restart, will retry on demand")

            self._set_diag(MODE_NORMAL, 0)
            return True

    # ════════════════════════════════════════════════════════
    #  Public API for entities
    # ════════════════════════════════════════════════════════

    def get_max_distance_m(self) -> float:
        return self._pend_dist_m

    def get_target_delay_s(self) -> int:
        return self._pend_delay_s

    def get_sensitivity(self) -> int:
        return self._pend_sens

    def get_gate_coeff_index(self) -> int:
        return self._pend_gate

    def get_diagnostic_text(self) -> str:
        if self.mode == MODE_NORMAL:
            return "正常模式"
        return f"配置模式 {self.progress}%"

    def get_distance_cm(self) -> int:
        """Return target distance in cm (integer).

        - Normal mode: real-time value or 2026 (no target)
        - Config mode: 0
        """
        if self.mode == MODE_CONFIG:
            return DISTANCE_CONFIG_MODE
        return self.distance_cm

    # ── setters ──

    def set_max_distance_m(self, value: float) -> None:
        self._pend_dist_m = round(value, 1)

    def set_target_delay_s(self, value: int) -> None:
        self._pend_delay_s = value

    def set_sensitivity(self, value: int) -> None:
        self._pend_sens = value

    def set_gate_coeff_index(self, value: int) -> None:
        self._pend_gate = value
