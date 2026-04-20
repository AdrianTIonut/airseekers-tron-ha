"""Sensor platform for Airseekers Tron."""
import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfArea, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AirseekersDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Airseekers sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinators = data["coordinators"]

    entities = []
    for sn, coordinator in coordinators.items():
        entities.extend([
            AirseekersStateSensor(coordinator, sn),
            AirseekersLastNotificationSensor(coordinator, sn),
            AirseekersTaskCountSensor(coordinator, sn),
            AirseekersMapCountSensor(coordinator, sn),
            AirseekersFirmwareSensor(coordinator, sn),
            AirseekersLastActiveSensor(coordinator, sn),
            AirseekersTotalAreaSensor(coordinator, sn),
            AirseekersTotalTimeSensor(coordinator, sn),
            AirseekersTotalTasksSensor(coordinator, sn),
            AirseekersIPSensor(coordinator, sn),
            AirseekersNightModeSensor(coordinator, sn),
        ])

    async_add_entities(entities)


class AirseekersBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Airseekers sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AirseekersDataCoordinator,
        sn: str,
        name: str,
        key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sn = sn
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{sn}_{key}"

    @property
    def device_info(self):
        """Return device info."""
        device = self.coordinator.data.get("device", {})
        return {
            "identifiers": {(DOMAIN, self._sn)},
            "name": f"Airseekers Tron {self._sn[-6:]}",
            "manufacturer": "Airseekers",
            "model": "Tron",
            "sw_version": device.get("firmware_ver"),
        }


class AirseekersStateSensor(AirseekersBaseSensor):
    """Sensor for mower state."""

    _attr_icon = "mdi:robot-mower"

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "State", "state")

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("state", "unknown")


class AirseekersLastNotificationSensor(AirseekersBaseSensor):
    """Sensor for last notification."""

    _attr_icon = "mdi:bell"

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Last Notification", "last_notification")

    @property
    def native_value(self) -> str:
        notifications = self.coordinator.data.get("notifications", [])
        if notifications:
            return notifications[0].get("content", "No notifications")
        return "No notifications"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        notifications = self.coordinator.data.get("notifications", [])
        if notifications:
            latest = notifications[0]
            return {
                "notify_type": latest.get("notify_type"),
                "created_at": latest.get("created_at"),
            }
        return {}


class AirseekersTaskCountSensor(AirseekersBaseSensor):
    """Sensor for scheduled task count."""

    _attr_icon = "mdi:calendar-check"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Scheduled Tasks", "task_count")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get("tasks", []))


class AirseekersMapCountSensor(AirseekersBaseSensor):
    """Sensor for map count."""

    _attr_icon = "mdi:map"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Maps", "map_count")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get("maps", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        maps = self.coordinator.data.get("maps", [])
        return {"map_names": [m.get("nick_name") or m.get("mapName") for m in maps]}


class AirseekersFirmwareSensor(AirseekersBaseSensor):
    """Sensor for firmware version."""

    _attr_icon = "mdi:chip"

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Firmware", "firmware")

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("firmware_version", "Unknown")


class AirseekersLastActiveSensor(AirseekersBaseSensor):
    """Sensor for last active time."""

    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Last Active", "last_active")

    @property
    def native_value(self) -> datetime | None:
        timestamp = self.coordinator.data.get("last_active")
        if timestamp:
            return datetime.fromtimestamp(timestamp)
        return None


class AirseekersTotalAreaSensor(AirseekersBaseSensor):
    """Sensor for total mowed area."""

    _attr_icon = "mdi:grass"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "m²"

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Total Mowed Area", "total_area")

    @property
    def native_value(self) -> int:
        return self.coordinator.data.get("total_mowed_area", 0)


class AirseekersTotalTimeSensor(AirseekersBaseSensor):
    """Sensor for total mowing time."""

    _attr_icon = "mdi:timer"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "h"

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Total Mowing Time", "total_time")

    @property
    def native_value(self) -> float:
        seconds = self.coordinator.data.get("total_mowing_time", 0)
        return round(seconds / 3600, 1)


class AirseekersTotalTasksSensor(AirseekersBaseSensor):
    """Sensor for total task count."""

    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Total Tasks Completed", "total_tasks")

    @property
    def native_value(self) -> int:
        return self.coordinator.data.get("total_task_count", 0)


class AirseekersIPSensor(AirseekersBaseSensor):
    """Sensor for IP address."""

    _attr_icon = "mdi:ip-network"

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "IP Address", "ip_address")

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("ip_address", "Unknown")


class AirseekersNightModeSensor(AirseekersBaseSensor):
    """Sensor for night mode schedule."""

    _attr_icon = "mdi:weather-night"

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Night Mode Schedule", "night_mode")

    @property
    def native_value(self) -> str:
        start = self.coordinator.data.get("night_mode_start", "22:00")
        end = self.coordinator.data.get("night_mode_end", "06:00")
        return f"{start} - {end}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "start_time": self.coordinator.data.get("night_mode_start"),
            "end_time": self.coordinator.data.get("night_mode_end"),
        }
