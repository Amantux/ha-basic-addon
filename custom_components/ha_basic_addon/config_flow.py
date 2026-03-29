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
    """Config flow for HA Basic Add-on.

    Discovery path (Supervisor):
        async_step_hassio  →  async_step_hassio_confirm  →  entry created
        (stores info)          (user confirms in UI)

    Manual path:
        async_step_user  →  entry created
    """

    VERSION = 1

    # Populated in async_step_hassio; read in async_step_hassio_confirm.
    _hassio_discovery: HassioServiceInfo | None = None

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> HaBasicAddonOptionsFlow:
        return HaBasicAddonOptionsFlow()

    # ------------------------------------------------------------------
    # Manual setup
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Supervisor discovery — two-step following the Mealie pattern
    # (homeassistant/components/mealie/config_flow.py)
    # ------------------------------------------------------------------

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> FlowResult:
        """Step 1: Triggered by Supervisor when the add-on advertises ha_basic_addon.

        SOURCE_HASSIO → async_step_hassio (homeassistant/components/hassio/discovery.py).
        We store the discovery payload and surface a confirmation card in the UI.
        We do NOT create the entry here — that lets the user acknowledge the discovery
        and gives us a chance to validate the connection first.
        """
        await self.async_set_unique_id(discovery_info.uuid)
        self._abort_if_unique_id_configured()

        self._hassio_discovery = discovery_info
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: User clicks the 'New device found' card and confirms.

        Validates the connection before creating the entry so a not-yet-ready
        add-on doesn't leave a broken config entry behind.
        """
        assert self._hassio_discovery is not None

        if user_input is None:
            # Show confirmation form — user sees the add-on name and clicks Submit.
            return self.async_show_form(
                step_id="hassio_confirm",
                description_placeholders={"addon": self._hassio_discovery.name},
            )

        port = int(self._hassio_discovery.config.get(CONF_PORT, DEFAULT_PORT))
        data = {CONF_HOST: DEFAULT_HOST, CONF_PORT: port}

        try:
            await self._async_validate_input(self.hass, data)
        except (ClientError, asyncio.TimeoutError) as exc:
            _LOGGER.warning("Add-on not reachable during discovery confirm: %s", exc)
            return self.async_abort(reason="cannot_connect")

        return self.async_create_entry(title=self._hassio_discovery.name, data=data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _async_validate_input(self, hass: HomeAssistant, data: dict[str, object]) -> None:
        session = aiohttp_client.async_get_clientsession(hass)
        url = build_health_url(str(data[CONF_HOST]), int(data[CONF_PORT]))
        async with session.get(url, timeout=_TIMEOUT) as response:
            response.raise_for_status()

    def _sanitize_host(self, host: str) -> str:
        return host.strip().rstrip("/")
