"""Sensor platform for Airseekers Tron."""
import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
)
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
            # State / task
            AirseekersStateSensor(coordinator, sn),
            AirseekersRunTimeSensor(coordinator, sn),
            AirseekersRemainingAreaSensor(coordinator, sn),
            AirseekersCurrentTotalAreaSensor(coordinator, sn),
            AirseekersTaskProgressSensor(coordinator, sn),
            # Battery
            AirseekersBatterySensor(coordinator, sn),
            AirseekersBatteryTempSensor(coordinator, sn),
            # Position & RTK
            AirseekersRtkQualitySensor(coordinator, sn),
            AirseekersSatellitesSensor(coordinator, sn),
            AirseekersLoraRssiSensor(coordinator, sn),
            AirseekersPositionSensor(coordinator, sn),
            AirseekersHeadingSensor(coordinator, sn),
            # Network
            AirseekersWifiSignalSensor(coordinator, sn),
            AirseekersWifiSsidSensor(coordinator, sn),
            AirseekersIPSensor(coordinator, sn),
            Airseekers4GIPSensor(coordinator, sn),
            # Versions
            AirseekersFirmwareSensor(coordinator, sn),
            AirseekersChassisBoardSensor(coordinator, sn),
            AirseekersCutterBoardSensor(coordinator, sn),
            AirseekersRtkBoardSensor(coordinator, sn),
            # Other
            AirseekersLastNotificationSensor(coordinator, sn),
            AirseekersLastActiveSensor(coordinator, sn),
            AirseekersNightModeSensor(coordinator, sn),
            AirseekersMapCountSensor(coordinator, sn),
            AirseekersTaskCountSensor(coordinator, sn),
            # Statistics (cumulative)
            AirseekersTotalAreaSensor(coordinator, sn),
            AirseekersTotalTimeSensor(coordinator, sn),
            AirseekersTotalTasksSensor(coordinator, sn),
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
        return {
            "identifiers": {(DOMAIN, self._sn)},
            "name": f"Airseekers Tron {self._sn[-6:]}",
            "manufacturer": "Airseekers",
            "model": "Tron",
            "sw_version": self.coordinator.data.get("firmware_version"),
        }


# ============================================================
# STATE & TASK
# ============================================================

class AirseekersStateSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:robot-mower"

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "State", "state")

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("state", "unknown")


class AirseekersRunTimeSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Current Task Run Time", "run_time")

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("run_time") or "00:00:00"


class AirseekersRemainingAreaSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:grass"
    _attr_native_unit_of_measurement = "m²"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Remaining Area", "remaining_area")

    @property
    def native_value(self):
        v = self.coordinator.data.get("remaining_area")
        return round(v, 1) if v is not None else None


class AirseekersCurrentTotalAreaSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:vector-square"
    _attr_native_unit_of_measurement = "m²"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Current Task Total Area", "current_total_area")

    @property
    def native_value(self):
        v = self.coordinator.data.get("current_total_area")
        return round(v, 1) if v is not None else None


class AirseekersTaskProgressSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:progress-check"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Task Progress", "task_progress")

    @property
    def native_value(self):
        total = self.coordinator.data.get("current_total_area")
        remaining = self.coordinator.data.get("remaining_area")
        if total and remaining is not None and total > 0:
            mowed = total - remaining
            return round((mowed / total) * 100, 1)
        return 0


# ============================================================
# BATTERY
# ============================================================

class AirseekersBatterySensor(AirseekersBaseSensor):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Battery", "battery")

    @property
    def native_value(self):
        return self.coordinator.data.get("battery_percentage")


class AirseekersBatteryTempSensor(AirseekersBaseSensor):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Battery Temperature", "battery_temp")

    @property
    def native_value(self):
        return self.coordinator.data.get("battery_temperature")


# ============================================================
# POSITION & RTK
# ============================================================

class AirseekersRtkQualitySensor(AirseekersBaseSensor):
    _attr_icon = "mdi:satellite-variant"

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "RTK Quality", "rtk_quality")

    @property
    def native_value(self):
        return self.coordinator.data.get("rtk_quality_state") or "unknown"


class AirseekersSatellitesSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:satellite"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Satellites", "satellites")

    @property
    def native_value(self):
        return self.coordinator.data.get("num_satellites")

    @property
    def extra_state_attributes(self):
        return {
            "satellites_used": self.coordinator.data.get("num_satellites_used"),
            "localization_state": self.coordinator.data.get("localization_state"),
            "ref_station_state": self.coordinator.data.get("ref_station_state"),
        }


class AirseekersLoraRssiSensor(AirseekersBaseSensor):
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "LoRa Signal", "lora_rssi")

    @property
    def native_value(self):
        return self.coordinator.data.get("lora_rssi")


class AirseekersPositionSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:map-marker"

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Position", "position")

    @property
    def native_value(self):
        lat = self.coordinator.data.get("robot_lat")
        lon = self.coordinator.data.get("robot_lon")
        if lat is not None and lon is not None:
            return f"{lat:.6f}, {lon:.6f}"
        return None

    @property
    def extra_state_attributes(self):
        return {
            "latitude": self.coordinator.data.get("robot_lat"),
            "longitude": self.coordinator.data.get("robot_lon"),
            "x": self.coordinator.data.get("robot_x"),
            "y": self.coordinator.data.get("robot_y"),
        }


class AirseekersHeadingSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:compass"
    _attr_native_unit_of_measurement = "°"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Heading", "heading")

    @property
    def native_value(self):
        import math
        yaw = self.coordinator.data.get("robot_yaw")
        if yaw is not None:
            # yaw is in radians, convert to degrees 0-360
            deg = math.degrees(yaw) % 360
            return round(deg, 1)
        return None


# ============================================================
# NETWORK
# ============================================================

class AirseekersWifiSignalSensor(AirseekersBaseSensor):
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "WiFi Signal", "wifi_dbm")

    @property
    def native_value(self):
        return self.coordinator.data.get("wifi_dbm")


class AirseekersWifiSsidSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:wifi"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "WiFi SSID", "wifi_ssid")

    @property
    def native_value(self):
        return self.coordinator.data.get("wifi_ssid") or "disconnected"


class AirseekersIPSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:ip-network"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "IP Address", "ip_address")

    @property
    def native_value(self):
        return self.coordinator.data.get("ip_address") or "Unknown"


class Airseekers4GIPSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:signal-4g"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "4G IP", "4g_ip")

    @property
    def native_value(self):
        return self.coordinator.data.get("wireless_4g_ip") or "none"

    @property
    def extra_state_attributes(self):
        return {
            "sim_active": self.coordinator.data.get("sim_active"),
        }


# ============================================================
# VERSIONS
# ============================================================

class AirseekersFirmwareSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:chip"

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Firmware", "firmware")

    @property
    def native_value(self):
        return self.coordinator.data.get("mower_package") or self.coordinator.data.get("firmware_version", "Unknown")


class AirseekersChassisBoardSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:chip"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Chassis Board", "chassis_board")

    @property
    def native_value(self):
        return self.coordinator.data.get("chassis_board")


class AirseekersCutterBoardSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:chip"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Cutter Board", "cutter_board")

    @property
    def native_value(self):
        return self.coordinator.data.get("cutter_board")


class AirseekersRtkBoardSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:chip"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "RTK Board", "rtk_board")

    @property
    def native_value(self):
        return self.coordinator.data.get("rtk_board")


# ============================================================
# OTHER
# ============================================================

class AirseekersLastNotificationSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:bell"

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Last Notification", "last_notification")

    @property
    def native_value(self):
        notifications = self.coordinator.data.get("notifications", [])
        if notifications:
            return notifications[0].get("content", "No notifications")
        return "No notifications"

    @property
    def extra_state_attributes(self):
        notifications = self.coordinator.data.get("notifications", [])
        if notifications:
            latest = notifications[0]
            return {
                "notify_type": latest.get("notify_type"),
                "notify_type_name": latest.get("notify_type_name"),
                "created_at": latest.get("created_at"),
            }
        return {}


class AirseekersLastActiveSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Last Active", "last_active")

    @property
    def native_value(self):
        timestamp = self.coordinator.data.get("last_active")
        if timestamp:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return None


class AirseekersNightModeSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:weather-night"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Night Mode Schedule", "night_mode")

    @property
    def native_value(self):
        start = self.coordinator.data.get("night_mode_start", "22:00")
        end = self.coordinator.data.get("night_mode_end", "06:00")
        return f"{start} - {end}"

    @property
    def extra_state_attributes(self):
        return {
            "start_time": self.coordinator.data.get("night_mode_start"),
            "end_time": self.coordinator.data.get("night_mode_end"),
        }


class AirseekersMapCountSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:map"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Maps", "map_count")

    @property
    def native_value(self):
        return len(self.coordinator.data.get("maps", []))

    @property
    def extra_state_attributes(self):
        maps = self.coordinator.data.get("maps", [])
        return {"map_names": [m.get("nick_name") or m.get("mapName") for m in maps]}


class AirseekersTaskCountSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:calendar-check"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Scheduled Tasks", "task_count")

    @property
    def native_value(self):
        return len(self.coordinator.data.get("tasks", []))


# ============================================================
# STATISTICS (cumulative from history)
# ============================================================

class AirseekersTotalAreaSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:grass"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "m²"

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Total Mowed Area", "total_area")

    @property
    def native_value(self):
        return self.coordinator.data.get("total_mowed_area", 0)


class AirseekersTotalTimeSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:timer"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "h"

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Total Mowing Time", "total_time")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("total_mowing_time", 0)
        return round(seconds / 3600, 1)


class AirseekersTotalTasksSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Total Tasks Completed", "total_tasks")

    @property
    def native_value(self):
        return self.coordinator.data.get("total_task_count", 0)
