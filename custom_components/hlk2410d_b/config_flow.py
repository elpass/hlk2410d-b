"""Config flow for HLK-LD2410D-B."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEVICE_NAME_PATTERN

_LOGGER = logging.getLogger(__name__)


class HLK2410DConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: dict[str, Any] = {}
        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}

    # ── Bluetooth discovery ──

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = {
            CONF_ADDRESS: discovery_info.address,
            CONF_NAME: discovery_info.name or "HLK-LD2410D-B",
        }
        self.context["title_placeholders"] = {"name": self._discovery_info[CONF_NAME]}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info[CONF_NAME],
                data=self._discovery_info,
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovery_info[CONF_NAME]},
        )

    # ── Manual (user) step ──

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            name = self._discovered[address].name or "HLK-LD2410D-B"
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=name,
                data={CONF_ADDRESS: address, CONF_NAME: name},
            )

        self._discovered = {}
        for info in async_discovered_service_info(self.hass, connectable=True):
            if info.name and DEVICE_NAME_PATTERN in info.name:
                self._discovered[info.address] = info

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        device_list = {
            addr: f"{si.name} ({addr})"
            for addr, si in self._discovered.items()
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In(device_list)}),
        )