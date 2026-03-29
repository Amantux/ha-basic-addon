from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientError
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import CONF_HOST, CONF_PORT, DEFAULT_HOST, DEFAULT_PORT, DOMAIN
from .helpers import build_health_url

_LOGGER = logging.getLogger(__name__)


class HaBasicAddonFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input: dict[str, object] | None = None):
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
        host = self._sanitize_host(str(discovery_info.get(CONF_HOST, DEFAULT_HOST)))
        port = int(discovery_info.get(CONF_PORT, DEFAULT_PORT))
        entry_data = {CONF_HOST: host, CONF_PORT: port}

        if self._async_abort_entries_match(entry_data):
            return self.async_abort(reason="already_configured")

        return self.async_create_entry(title="HA Basic Add-on", data=entry_data)

    async def _async_validate_input(self, hass: HomeAssistant, data: dict[str, object]) -> None:
        session = aiohttp_client.async_get_clientsession(hass)
        host = str(data[CONF_HOST])
        port = int(data[CONF_PORT])
        url = build_health_url(host, port)
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()

    def _sanitize_host(self, host: str) -> str:
        sanitized = host.strip()
        return sanitized.rstrip("/")
