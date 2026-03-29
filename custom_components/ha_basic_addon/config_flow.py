from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientError, ClientTimeout
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import CONF_HOST, CONF_PORT, DEFAULT_HOST, DEFAULT_PORT, DOMAIN
from .helpers import build_health_url

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = ClientTimeout(total=10)


class HaBasicAddonFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, object] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            sanitized_host = self._sanitize_host(user_input[CONF_HOST])
            entry_data = {
                CONF_HOST: sanitized_host,
                CONF_PORT: int(user_input[CONF_PORT]),
            }
            try:
                await self._async_validate_input(self.hass, entry_data)
            except (ClientError, asyncio.TimeoutError) as exc:
                _LOGGER.warning("Error reaching add-on health endpoint: %s", exc)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="HA Basic Add-on", data=entry_data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def async_step_discovery(self, discovery_info: dict[str, Any]) -> FlowResult:
        """Handle Supervisor discovery — fires when the add-on advertises ha_basic_addon."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        host = self._sanitize_host(str(discovery_info.get(CONF_HOST, DEFAULT_HOST)))
        port = int(discovery_info.get(CONF_PORT, DEFAULT_PORT))
        return self.async_create_entry(
            title="HA Basic Add-on",
            data={CONF_HOST: host, CONF_PORT: port},
        )

    async def _async_validate_input(self, hass: HomeAssistant, data: dict[str, object]) -> None:
        session = aiohttp_client.async_get_clientsession(hass)
        url = build_health_url(str(data[CONF_HOST]), int(data[CONF_PORT]))
        async with session.get(url, timeout=_TIMEOUT) as response:
            response.raise_for_status()

    def _sanitize_host(self, host: str) -> str:
        return host.strip().rstrip("/")
