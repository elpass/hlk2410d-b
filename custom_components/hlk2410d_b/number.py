"""Number entities for HLK-LD2410D-B."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    KEY_MAX_DISTANCE,
    KEY_TARGET_DELAY,
    MAX_DISTANCE_MIN_RAW,
    MAX_DISTANCE_MAX_RAW,
    TARGET_DELAY_MIN,
    TARGET_DELAY_MAX,
)
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
        HLK2410DMaxDistance(coordinator, entry),
        HLK2410DTargetDelay(coordinator, entry),
    ])


class HLK2410DMaxDistance(HLK2410DEntity, NumberEntity):
    """Max distance in metres (0.1 m resolution)."""

    _attr_name = "最大距离"
    _attr_native_min_value = MAX_DISTANCE_MIN_RAW / 10.0   # 0.7
    _attr_native_max_value = MAX_DISTANCE_MAX_RAW / 10.0   # 10.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = "m"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: HLK2410DCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, KEY_MAX_DISTANCE)

    @property
    def native_value(self) -> float:
        return self.coordinator.get_max_distance_m()

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_max_distance_m(value)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_params_{self._entry.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class HLK2410DTargetDelay(HLK2410DEntity, NumberEntity):
    """Target disappearance delay in seconds."""

    _attr_name = "目标消失延迟"
    _attr_native_min_value = TARGET_DELAY_MIN
    _attr_native_max_value = TARGET_DELAY_MAX
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "s"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: HLK2410DCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, KEY_TARGET_DELAY)

    @property
    def native_value(self) -> int:
        return self.coordinator.get_target_delay_s()

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_target_delay_s(int(value))
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_params_{self._entry.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()