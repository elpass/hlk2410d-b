"""Select entities for HLK-LD2410D-B."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_SENSITIVITY, KEY_GATE_COEFF
from .coordinator import HLK2410DCoordinator
from .entity import HLK2410DEntity

_LOGGER = logging.getLogger(__name__)

LEVEL_OPTIONS = ["1", "2", "3", "4", "5"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HLK2410DCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        HLK2410DSensitivity(coordinator, entry),
        HLK2410DGateCoeff(coordinator, entry),
    ])


class HLK2410DSensitivity(HLK2410DEntity, SelectEntity):
    """Sensitivity 1-5."""

    _attr_name = "灵敏度设置"
    _attr_options = LEVEL_OPTIONS

    def __init__(self, coordinator: HLK2410DCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, KEY_SENSITIVITY)

    @property
    def current_option(self) -> str:
        return str(self.coordinator.get_sensitivity())

    async def async_select_option(self, option: str) -> None:
        self.coordinator.set_sensitivity(int(option))
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


class HLK2410DGateCoeff(HLK2410DEntity, SelectEntity):
    """Gate-threshold coefficient 1-5 (→ 1, 5, 10, 15, 20)."""

    _attr_name = "门限生成系数"
    _attr_options = LEVEL_OPTIONS

    def __init__(self, coordinator: HLK2410DCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, KEY_GATE_COEFF)

    @property
    def current_option(self) -> str:
        return str(self.coordinator.get_gate_coeff_index())

    async def async_select_option(self, option: str) -> None:
        self.coordinator.set_gate_coeff_index(int(option))
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