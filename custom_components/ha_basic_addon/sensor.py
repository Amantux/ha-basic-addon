from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import AddEntitiesCallback, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HaBasicAddonDataUpdateCoordinator


class HaBasicAddonSensor(CoordinatorEntity, SensorEntity):
    coordinator: HaBasicAddonDataUpdateCoordinator

    def __init__(self, coordinator: HaBasicAddonDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "Basic Add-on Health"
        self._attr_unique_id = f"{DOMAIN}_health"
        self._attr_attribution = "Powered by HA Basic Add-on"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "basic-service")},
            name="HA Basic Add-on",
            manufacturer="Community",
        )

    @property
    def native_value(self) -> str | None:
        if not (data := self.coordinator.data):
            return None
        return data.get("status")

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        data = self.coordinator.data or {}
        return {
            "greeting": data.get("greeting"),
            "uptime": data.get("uptime"),
            "path": data.get("path"),
            "timestamp": data.get("timestamp"),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HaBasicAddonSensor(coordinator)], True)
