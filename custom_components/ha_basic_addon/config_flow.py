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

    Supervisor discovery path (preferred — zero user typing):
        async_step_hassio         validate connection; abort early if add-on not ready
            ↓
        async_step_hassio_confirm  _set_confirm_only() → surfaces "New device found" badge
            ↓ (user clicks Submit)
        async_create_entry

    Manual path:
        async_step_user  →  validate  →  async_create_entry
    """

    VERSION = 1

    # Set in async_step_hassio; read in async_step_hassio_confirm.
    _hassio_discovery: HassioServiceInfo | None = None

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HaBasicAddonOptionsFlow:
        return HaBasicAddonOptionsFlow()

    # ------------------------------------------------------------------
    # Supervisor discovery — follows HA quality-scale pattern:
    # https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/discovery/
    # ------------------------------------------------------------------

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> FlowResult:
        """Step 1 — called by Supervisor when the add-on advertises ha_basic_addon.

        Per the HA discovery quality-scale rule, validation happens HERE (not in
        the confirm step) so a not-yet-ready add-on aborts cleanly before any UI
        is shown.  We also pass `updates` to _abort_if_unique_id_configured so that
        a port change on the running add-on is silently applied to the existing entry
        rather than triggering a duplicate-detection abort.
        """
        port = int(discovery_info.config.get(CONF_PORT, DEFAULT_PORT))

        await self.async_set_unique_id(discovery_info.uuid)
        # If already configured, update the port if it changed and stop the flow.
        self._abort_if_unique_id_configured(updates={CONF_PORT: port})

        # Validate the connection now — abort before showing any UI if unreachable.
        try:
            await self._async_validate_input(
                self.hass, {CONF_HOST: DEFAULT_HOST, CONF_PORT: port}
            )
        except (ClientError, asyncio.TimeoutError) as exc:
            _LOGGER.debug("Add-on not reachable during Supervisor discovery: %s", exc)
            return self.async_abort(reason="cannot_connect")

        self._hassio_discovery = discovery_info
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2 — confirmation form.

        `_set_confirm_only()` marks the form as having no data fields — just a
        Submit button.  This is what causes HA to surface the "New device found"
        notification badge in Settings → Devices & Services.  Without this call
        the flow is registered internally but the badge never appears.
        """
        assert self._hassio_discovery is not None

        if user_input is not None:
            # Connection was already validated in async_step_hassio — create immediately.
            port = int(self._hassio_discovery.config.get(CONF_PORT, DEFAULT_PORT))
            return self.async_create_entry(
                title=self._hassio_discovery.name,
                data={CONF_HOST: DEFAULT_HOST, CONF_PORT: port},
            )

        # No user_input yet — show the confirm form.
        self._set_confirm_only()
        return self.async_show_form(
            step_id="hassio_confirm",
            description_placeholders={"addon": self._hassio_discovery.name},
        )

    # ------------------------------------------------------------------
    # Manual setup
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, object] | None = None
    ) -> FlowResult:
        """Manual setup via Settings → Devices & Services → Add integration."""
        errors: dict[str, str] = {}
        if user_input is not None:
            entry_data = {
                CONF_HOST: self._sanitize_host(str(user_input[CONF_HOST])),
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
    # Helpers
    # ------------------------------------------------------------------

    async def _async_validate_input(
        self, hass: HomeAssistant, data: dict[str, object]
    ) -> None:
        """Hit the /health endpoint; raise ClientError or TimeoutError on failure."""
        session = aiohttp_client.async_get_clientsession(hass)
        url = build_health_url(str(data[CONF_HOST]), int(data[CONF_PORT]))
        async with session.get(url, timeout=_TIMEOUT) as response:
            response.raise_for_status()

    @staticmethod
    def _sanitize_host(host: str) -> str:
        return host.strip().rstrip("/")
