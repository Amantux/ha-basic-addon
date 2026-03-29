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
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .helpers import build_health_url

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = ClientTimeout(total=10)


class HaBasicAddonOptionsFlow(config_entries.OptionsFlow):
    """Options flow — lets users tune the integration after setup."""

    async def async_step_init(
        self, user_input: dict[str, object] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=int(current.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)),
                    ): vol.All(int, vol.Range(min=10, max=3600)),
                }
            ),
        )


class HaBasicAddonFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> HaBasicAddonOptionsFlow:
        return HaBasicAddonOptionsFlow()

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

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> FlowResult:
        """Handle Supervisor discovery (SOURCE_HASSIO → async_step_hassio).

        Called when the add-on's config.json lists this domain under "discovery".
        discovery_info fields: config (dict), name (str), slug (str), uuid (str).
        Citation: homeassistant/components/hassio/discovery.py → async_create_flow
                  with context={"source": SOURCE_HASSIO}
        """
        await self.async_set_unique_id(discovery_info.uuid)
        self._abort_if_unique_id_configured()

        # config["host"] is the add-on's *bind* address (0.0.0.0), not routable.
        # On Supervisor the add-on and HA share the host — connect via 127.0.0.1.
        port = int(discovery_info.config.get(CONF_PORT, DEFAULT_PORT))
        return self.async_create_entry(
            title=discovery_info.name,
            data={CONF_HOST: DEFAULT_HOST, CONF_PORT: port},
        )

    async def _async_validate_input(self, hass: HomeAssistant, data: dict[str, object]) -> None:
        session = aiohttp_client.async_get_clientsession(hass)
        url = build_health_url(str(data[CONF_HOST]), int(data[CONF_PORT]))
        async with session.get(url, timeout=_TIMEOUT) as response:
            response.raise_for_status()

    def _sanitize_host(self, host: str) -> str:
        return host.strip().rstrip("/")
