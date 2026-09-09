"""Button entities for HLK-LD2410D-B."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_BTN_READ, KEY_BTN_SET, KEY_BTN_RESTART
from .coordinator import HLK2410DCoordinator
from .entity import HLK2410DEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HLK2410DCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        HLK2410DReadButton(coordinator, entry),
        HLK2410DSetButton(coordinator, entry),
        HLK2410DRestartButton(coordinator, entry),
    ])


class HLK2410DReadButton(HLK2410DEntity, ButtonEntity):
    """Read parameters from module."""

    _attr_name = "读取"
    _attr_icon = "mdi:download"

    def __init__(self, coordinator: HLK2410DCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, KEY_BTN_READ)

    async def async_press(self) -> None:
        _LOGGER.info("Read button pressed")
        if not await self.coordinator.read_parameters():
            _LOGGER.error("Read parameters failed")


class HLK2410DSetButton(HLK2410DEntity, ButtonEntity):
    """Write changed parameters to module."""

    _attr_name = "设置"
    _attr_icon = "mdi:upload"

    def __init__(self, coordinator: HLK2410DCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, KEY_BTN_SET)

    async def async_press(self) -> None:
        _LOGGER.info("Set button pressed")
        ok, msg = await self.coordinator.set_parameters()
        _LOGGER.info("Set result: %s (ok=%s)", msg, ok)


class HLK2410DRestartButton(HLK2410DEntity, ButtonEntity):
    """Restart module (fire-and-forget + countdown + reconnect)."""

    _attr_name = "重启"
    _attr_icon = "mdi:restart"

    def __init__(self, coordinator: HLK2410DCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, KEY_BTN_RESTART)

    async def async_press(self) -> None:
        _LOGGER.info("Restart button pressed – module will reboot and reconnect")
        ok = await self.coordinator.restart_module()
        if ok:
            _LOGGER.info("Restart sequence completed, BLE reconnected")
        else:
            _LOGGER.error("Restart sequence failed")
