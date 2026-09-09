"""Sensor entities (distance + diagnostic) for HLK-LD2410D-B."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_TARGET_DISTANCE, KEY_DIAGNOSTIC
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
        HLK2410DDistanceSensor(coordinator, entry),
        HLK2410DDiagnosticSensor(coordinator, entry),
    ])


class HLK2410DDistanceSensor(HLK2410DEntity, SensorEntity):
    """Target distance sensor (integer cm).

    Values:
      - Normal mode, target detected: distance in cm (e.g. 124)
      - Normal mode, no target:       2026
      - Config mode:                  0
    """

    _attr_name = "目标距离"
    _attr_icon = "mdi:radar"
    _attr_native_unit_of_measurement = "cm"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: HLK2410DCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, KEY_TARGET_DISTANCE)

    @property
    def native_value(self) -> int:
        return self.coordinator.get_distance_cm()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        for suffix in ("distance", "diagnostic"):
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass,
                    f"{DOMAIN}_{suffix}_{self._entry.entry_id}",
                    self._handle_update,
                )
            )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class HLK2410DDiagnosticSensor(HLK2410DEntity, SensorEntity):
    """Diagnostic: mode + progress."""

    _attr_name = "诊断"
    _attr_icon = "mdi:information-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HLK2410DCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, KEY_DIAGNOSTIC)

    @property
    def native_value(self) -> str:
        return self.coordinator.get_diagnostic_text()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_diagnostic_{self._entry.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
