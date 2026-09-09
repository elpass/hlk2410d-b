"""Base entity for HLK-LD2410D-B."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .coordinator import HLK2410DCoordinator


class HLK2410DEntity(Entity):
    """Base entity class."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: HLK2410DCoordinator,
        entry: ConfigEntry,
        entity_key: str,
    ) -> None:
        self.coordinator = coordinator
        self._entry = entry
        self._entity_key = entity_key
        self._attr_unique_id = f"{entry.unique_id}_{entity_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="Hi-Link",
            model="HLK-LD2410D-B",
            sw_version="1.0",
        )