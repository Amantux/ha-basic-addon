from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError, ClientSession
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_HOST, CONF_PORT, DOMAIN
from .helpers import build_health_url

LOG = logging.getLogger(__name__)


class HaBasicAddonDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, session: ClientSession, entry: ConfigEntry) -> None:
        self._session = session
        self._url = build_health_url(entry.data[CONF_HOST], int(entry.data[CONF_PORT]))
        super().__init__(
            hass,
            LOG,
            name="ha_basic_addon",
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            async with self._session.get(self._url, timeout=10) as response:
                response.raise_for_status()
                return await response.json()
        except ClientError as err:
            raise UpdateFailed(f"Error fetching add-on health: {err}") from err

