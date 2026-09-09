"""The HLK-LD2410D-B integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .ble_manager import BLEManager
from .coordinator import HLK2410DCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HLK-LD2410D-B from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    address: str = entry.data[CONF_ADDRESS]
    name: str = entry.data[CONF_NAME]

    ble = BLEManager(hass, address, name)
    coordinator = HLK2410DCoordinator(hass, ble, entry.entry_id)

    hass.data[DOMAIN][entry.entry_id] = coordinator

    connected = await ble.connect()
    if not connected:
        _LOGGER.warning(
            "Initial connect to %s (%s) failed – will retry on demand", name, address
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: HLK2410DCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.ble.disconnect()
    return unload_ok
