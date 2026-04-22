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
    UnitOfLength,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    LOCALIZATION_STATE_LABELS,
    NET_TYPE_LABELS,
    NRTK_BIND_TYPE_LABELS,
    REF_STATION_STATE_LABELS,
    RTK_STATUS_LABELS,
    TASK_STATE_LABELS,
    TASK_TYPE_LABELS,
    UPGRADE_STATE_LABELS,
)
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
            # ---- NEW sensors (v1.1) ----
            AirseekersBatteryErrorCodeSensor(coordinator, sn),
            AirseekersRtkSnrSensor(coordinator, sn),
            AirseekersRtkNumSensor(coordinator, sn),
            AirseekersRtkVersionSensor(coordinator, sn),
            AirseekersRtkBaseSnSensor(coordinator, sn),
            AirseekersVoiceVersionSensor(coordinator, sn),
            AirseekersVoiceLanguageSensor(coordinator, sn),
            AirseekersVoiceNewVersionSensor(coordinator, sn),
            AirseekersFirmwareProgressSensor(coordinator, sn),
            AirseekersFirmwareStateSensor(coordinator, sn),
            AirseekersMcuProgressSensor(coordinator, sn),
            AirseekersMcuStateSensor(coordinator, sn),
            AirseekersNetTypeSensor(coordinator, sn),
            AirseekersSimIccidSensor(coordinator, sn),
            AirseekersAltitudeSensor(coordinator, sn),
            AirseekersLocalizationStateSensor(coordinator, sn),
            AirseekersRefStationStateSensor(coordinator, sn),
            AirseekersRtkFixSensor(coordinator, sn),
            AirseekersTaskStateSensor(coordinator, sn),
            AirseekersTaskTypeSensor(coordinator, sn),
            AirseekersNrtkBindTypeSensor(coordinator, sn),
            AirseekersNrtkTrialRemainingSensor(coordinator, sn),
            AirseekersSensorStatusRawSensor(coordinator, sn),
            AirseekersWarrantyDaysSensor(coordinator, sn),
            AirseekersWarrantyEndSensor(coordinator, sn),
            AirseekersExtendedWarrantyEndSensor(coordinator, sn),
            AirseekersLastTaskDurationSensor(coordinator, sn),
            AirseekersLastTaskAreaSensor(coordinator, sn),
            AirseekersLastTaskEndSensor(coordinator, sn),
            AirseekersLastTaskResultSensor(coordinator, sn),
            # ---- v1.2 gap-analysis additions -----------------------------
            AirseekersExploreStateSensor(coordinator, sn),
            AirseekersVoiceUpgradeProgressSensor(coordinator, sn),
            AirseekersVoiceUpgradeStateSensor(coordinator, sn),
            AirseekersWifiIPSensor(coordinator, sn),
            AirseekersFirmwareLatestSensor(coordinator, sn),
            AirseekersRtkChannelSensor(coordinator, sn),
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



# ============================================================
# NEW v1.1 SENSORS — derived from full_status fields that were
# already fetched but never exposed, plus the new endpoints.
# ============================================================


def _ts_to_dt(value):
    """Convert unix epoch (int/float, seconds) to tz-aware datetime."""
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    return None


class AirseekersBatteryErrorCodeSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:battery-alert-variant"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Battery Error Code", "battery_error_code")

    @property
    def native_value(self):
        return self.coordinator.data.get("battery_error")


class AirseekersRtkSnrSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:signal-variant"
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "RTK SNR", "rtk_snr")

    @property
    def native_value(self):
        return self.coordinator.data.get("rtk_snr")


class AirseekersRtkNumSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:numeric"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "RTK Packet Count", "rtk_num")

    @property
    def native_value(self):
        return self.coordinator.data.get("rtk_num")


class AirseekersRtkVersionSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "RTK Base Firmware", "rtk_base_firmware")

    @property
    def native_value(self):
        return self.coordinator.data.get("rtk_version")


class AirseekersRtkBaseSnSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:serial-port"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "RTK Base Serial", "rtk_base_sn")

    @property
    def native_value(self):
        value = self.coordinator.data.get("rtk_base_sn")
        return value or None


class AirseekersVoiceVersionSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:microphone-message"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Voice Pack Version", "voice_version")

    @property
    def native_value(self):
        return self.coordinator.data.get("voice_version")


class AirseekersVoiceLanguageSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:translate"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Voice Language", "voice_language")

    @property
    def native_value(self):
        return self.coordinator.data.get("voice_language")


class AirseekersVoiceNewVersionSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:cloud-download"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Voice Pack Latest", "voice_latest")

    @property
    def native_value(self):
        return self.coordinator.data.get("voice_new_version")

    @property
    def extra_state_attributes(self):
        return {
            "current_version": self.coordinator.data.get("voice_current_version"),
            "upgradable": self.coordinator.data.get("voice_upgradable"),
            "change_log": self.coordinator.data.get("voice_change_log"),
        }


class AirseekersFirmwareProgressSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:progress-upload"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Firmware Upgrade Progress", "firmware_progress")

    @property
    def native_value(self):
        return self.coordinator.data.get("firmware_upgrade_progress")


class AirseekersFirmwareStateSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:cog-sync"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Firmware Upgrade State", "firmware_state")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("firmware_upgrade_state")
        return UPGRADE_STATE_LABELS.get(raw, raw)


class AirseekersMcuProgressSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:progress-upload"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "MCU Upgrade Progress", "mcu_progress")

    @property
    def native_value(self):
        return self.coordinator.data.get("mcu_upgrade_progress")


class AirseekersMcuStateSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "MCU Upgrade State", "mcu_state")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("mcu_upgrade_state")
        return UPGRADE_STATE_LABELS.get(raw, raw)


class AirseekersNetTypeSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Active Network", "net_type")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("net_info_type")
        return NET_TYPE_LABELS.get(raw, "unknown")


class AirseekersSimIccidSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:sim"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "SIM ICCID", "sim_iccid")

    @property
    def native_value(self):
        return self.coordinator.data.get("iccid")


class AirseekersAltitudeSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:elevation-rise"
    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Altitude", "altitude")

    @property
    def native_value(self):
        value = self.coordinator.data.get("robot_altitude")
        if isinstance(value, (int, float)):
            return round(float(value), 2)
        return None


class AirseekersLocalizationStateSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:crosshairs-gps"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Localization State", "localization_state")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("localization_state")
        return LOCALIZATION_STATE_LABELS.get(raw, raw)


class AirseekersRefStationStateSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:radio-tower"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "RTK Base State", "ref_station_state")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("ref_station_state")
        return REF_STATION_STATE_LABELS.get(raw, raw)


class AirseekersRtkFixSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:satellite-uplink"

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "RTK Fix", "rtk_fix")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("rtk_quality_state")
        return RTK_STATUS_LABELS.get(raw, raw)


class AirseekersTaskStateSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:state-machine"

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Task Phase", "task_phase")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("task_state")
        return TASK_STATE_LABELS.get(raw, raw)


class AirseekersTaskTypeSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:shape"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Task Type", "task_type")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("task_type")
        return TASK_TYPE_LABELS.get(raw, raw)


class AirseekersNrtkBindTypeSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:key-variant"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "NRTK Plan", "nrtk_plan")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("nrtk_bind_type")
        return NRTK_BIND_TYPE_LABELS.get(raw, raw)

    @property
    def extra_state_attributes(self):
        return {
            "active_status": self.coordinator.data.get("nrtk_active_status"),
            "trial_available": self.coordinator.data.get("nrtk_trial_available"),
            "trial_duration_months": self.coordinator.data.get("nrtk_trial_duration"),
        }


class AirseekersNrtkTrialRemainingSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:clock-time-eight-outline"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "NRTK Trial Remaining", "nrtk_trial_remaining")

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("nrtk_trial_remaining")
        if isinstance(seconds, (int, float)) and seconds > 0:
            return round(seconds / 86400, 1)
        return None


class AirseekersSensorStatusRawSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:bit-check"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Sensor Status (raw)", "sensor_status_raw")

    @property
    def native_value(self):
        return self.coordinator.data.get("sensor_status_raw")

    @property
    def extra_state_attributes(self):
        value = self.coordinator.data.get("sensor_status_raw")
        if not isinstance(value, int):
            return {}
        from .const import SENSOR_STATUS_BITS
        active = [label for bit, label in SENSOR_STATUS_BITS.items() if value & (1 << bit)]
        return {"hex": f"0x{value:X}", "active_bits": active}


class AirseekersWarrantyDaysSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:shield-check"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Warranty Days Left", "warranty_days")

    @property
    def native_value(self):
        end = self.coordinator.data.get("warranty_end")
        if isinstance(end, (int, float)) and end > 0:
            delta = end - datetime.now(tz=timezone.utc).timestamp()
            return max(0, round(delta / 86400))
        return None


class AirseekersWarrantyEndSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:calendar-end"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Warranty End", "warranty_end")

    @property
    def native_value(self):
        return _ts_to_dt(self.coordinator.data.get("warranty_end"))

    @property
    def extra_state_attributes(self):
        return {
            "warranty_start": _ts_to_dt(self.coordinator.data.get("warranty_start")),
            "has_extended": self.coordinator.data.get("has_extended_warranty"),
        }


class AirseekersExtendedWarrantyEndSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:calendar-end-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Extended Warranty End", "extended_warranty_end")

    @property
    def native_value(self):
        return _ts_to_dt(self.coordinator.data.get("extended_warranty_end"))


class AirseekersLastTaskDurationSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:timer-check"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Last Task Duration", "last_task_duration")

    @property
    def native_value(self):
        rec = self.coordinator.data.get("last_task_record")
        if not rec:
            return None
        seconds = rec.get("duration")
        if isinstance(seconds, (int, float)) and seconds > 0:
            return round(seconds / 60, 1)
        return None


class AirseekersLastTaskAreaSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:grass"
    _attr_native_unit_of_measurement = "m²"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Last Task Area", "last_task_area")

    @property
    def native_value(self):
        rec = self.coordinator.data.get("last_task_record")
        if not rec:
            return None
        raw = rec.get("mow_area") or rec.get("total_area")
        try:
            return round(float(raw), 1) if raw not in (None, "") else None
        except (TypeError, ValueError):
            return None


class AirseekersLastTaskEndSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:calendar-clock"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Last Task End", "last_task_end")

    @property
    def native_value(self):
        rec = self.coordinator.data.get("last_task_record")
        if not rec:
            return None
        return _ts_to_dt(rec.get("end_time") or rec.get("updated_at"))

    @property
    def extra_state_attributes(self):
        rec = self.coordinator.data.get("last_task_record") or {}
        return {
            "task_name": rec.get("task_name"),
            "task_type": rec.get("task_type"),
            "start_type": rec.get("start_type"),
            "picture_url": rec.get("picture_url") or None,
            "map_url": rec.get("map_url") or None,
        }




class AirseekersLastTaskResultSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:flag-checkered"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Last Task Result", "last_task_result")

    @property
    def native_value(self):
        rec = self.coordinator.data.get("last_task_record")
        if not rec:
            return None
        result = rec.get("result")
        if result == 0:
            return "success"
        if result is None:
            return None
        return f"error {result}"


# ============================================================
# v1.2 GAP-ANALYSIS ADDITIONS
# Derived from full_status + /firmware/latest fields that were in
# the dump but previously not mapped to entities.
# ============================================================


EXPLORE_STATE_LABELS = {
    0: "idle",
    1: "mapping",
    2: "paused",
    3: "finishing",
    4: "error",
}


class AirseekersExploreStateSensor(AirseekersBaseSensor):
    """Exposes full_status.explore_mapping_info (live mapping session)."""

    _attr_icon = "mdi:map-plus"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Explore State", "explore_state")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("explore_state")
        return EXPLORE_STATE_LABELS.get(raw, raw)

    @property
    def extra_state_attributes(self):
        return {
            "boundary_poses": self.coordinator.data.get("explore_boundary_poses"),
            "trajectory_poses": self.coordinator.data.get("explore_trajectory_poses"),
        }


class AirseekersVoiceUpgradeProgressSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:progress-upload"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Voice Upgrade Progress", "voice_upgrade_progress")

    @property
    def native_value(self):
        return self.coordinator.data.get("voice_upgrade_progress")


class AirseekersVoiceUpgradeStateSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:cog-sync"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Voice Upgrade State", "voice_upgrade_state")

    @property
    def native_value(self):
        raw = self.coordinator.data.get("voice_upgrade_state")
        return UPGRADE_STATE_LABELS.get(raw, raw)


class AirseekersWifiIPSensor(AirseekersBaseSensor):
    _attr_icon = "mdi:ip-network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "WiFi IP", "wifi_ip")

    @property
    def native_value(self):
        value = self.coordinator.data.get("wifi_ip")
        return value if value else "disconnected"


class AirseekersFirmwareLatestSensor(AirseekersBaseSensor):
    """Latest firmware version advertised by the cloud (from /firmware/latest)."""

    _attr_icon = "mdi:cloud-download"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "Firmware Latest", "firmware_latest")

    @property
    def native_value(self):
        return self.coordinator.data.get("firmware_latest_version")

    @property
    def extra_state_attributes(self):
        return {
            "current_version": self.coordinator.data.get("firmware_current_version"),
            "upgradable": self.coordinator.data.get("firmware_upgradable"),
            "force_upgrade": self.coordinator.data.get("firmware_force_upgrade"),
            "change_log": self.coordinator.data.get("firmware_change_log"),
        }


class AirseekersRtkChannelSensor(AirseekersBaseSensor):
    """Currently active LoRa channel/address pair on the RTK radio."""

    _attr_icon = "mdi:radio-tower"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, sn):
        super().__init__(coordinator, sn, "RTK LoRa Channel", "rtk_lora_channel")

    @property
    def native_value(self):
        return self.coordinator.data.get("rtk_channel_active")

    @property
    def extra_state_attributes(self):
        return {
            "address": self.coordinator.data.get("rtk_addr_active"),
            "quality": self.coordinator.data.get("rtk_quality_numeric"),
        }
