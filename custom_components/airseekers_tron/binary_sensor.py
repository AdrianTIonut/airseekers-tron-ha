"""Binary sensor platform for Airseekers Tron."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    """Set up Airseekers binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinators = data["coordinators"]

    entities = []
    for sn, coordinator in coordinators.items():
        entities.extend([
            AirseekersOnlineSensor(coordinator, sn),
            AirseekersNrtkSensor(coordinator, sn),
            AirseekersOtaAvailableSensor(coordinator, sn),
            AirseekersChargingSensor(coordinator, sn),
            # v1.2 additions from gap analysis vs. APK dump
            AirseekersFirmwareUpgradableSensor(coordinator, sn),
            AirseekersVoiceUpgradableSensor(coordinator, sn),
            AirseekersLegacyTaskSensor(coordinator, sn),
            AirseekersDeviceLockedSensor(coordinator, sn),
        ])

    async_add_entities(entities)


class AirseekersBaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base class for Airseekers binary sensors."""

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


class AirseekersOnlineSensor(AirseekersBaseBinarySensor):
    """Binary sensor for online status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Online", "online")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.get("online", False)


class AirseekersNrtkSensor(AirseekersBaseBinarySensor):
    """Binary sensor for NRTK (RTK) status."""

    _attr_icon = "mdi:satellite-variant"

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "RTK Available", "nrtk")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.get("nrtk_available", False)

    @property
    def extra_state_attributes(self):
        return {
            "nrtk_bound": self.coordinator.data.get("nrtk_bound"),
        }


class AirseekersOtaAvailableSensor(AirseekersBaseBinarySensor):
    """Binary sensor for MCU OTA availability (from full_status.upgrade_mcu_status)."""

    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "MCU Upgrade Available", "ota_available")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("mcu_upgrade_available", False))

    @property
    def extra_state_attributes(self):
        return {
            "current_mcu": self.coordinator.data.get("mcu_current_version"),
            "target_mcu": self.coordinator.data.get("mcu_target_version"),
        }


class AirseekersChargingSensor(AirseekersBaseBinarySensor):
    """Binary sensor: true if robot is on dock / charging."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Charging", "charging")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.get("state") == "charging"


class AirseekersFirmwareUpgradableSensor(AirseekersBaseBinarySensor):
    """True if a mower firmware upgrade is available (from /firmware/latest)."""

    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Firmware Upgrade Available", "firmware_upgradable")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("firmware_upgradable", False))

    @property
    def extra_state_attributes(self):
        return {
            "latest_version": self.coordinator.data.get("firmware_latest_version"),
            "current_version": self.coordinator.data.get("firmware_current_version"),
            "force_upgrade": self.coordinator.data.get("firmware_force_upgrade"),
            "change_log": self.coordinator.data.get("firmware_change_log"),
        }


class AirseekersVoiceUpgradableSensor(AirseekersBaseBinarySensor):
    """True if a voice-pack upgrade is available (from /voice-version/latest)."""

    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Voice Pack Upgrade Available", "voice_upgradable")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("voice_upgradable", False))

    @property
    def extra_state_attributes(self):
        return {
            "current_version": self.coordinator.data.get("voice_current_version"),
            "new_version": self.coordinator.data.get("voice_new_version"),
            "change_log": self.coordinator.data.get("voice_change_log"),
        }


class AirseekersLegacyTaskSensor(AirseekersBaseBinarySensor):
    """True if the robot has an interrupted task awaiting resume.

    Surfaces ``full_status.task_status.is_has_legacy_task``. When on, the
    previous mowing session was interrupted (power loss, manual stop, etc.)
    and can be resumed or discarded via the app.
    """

    _attr_icon = "mdi:content-save-alert"

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Legacy Task Pending", "legacy_task")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("has_legacy_task", False))

    @property
    def extra_state_attributes(self):
        return {
            "legacy_task_id": self.coordinator.data.get("legacy_task_id") or None,
            "map_id": self.coordinator.data.get("current_map_id"),
        }


class AirseekersDeviceLockedSensor(AirseekersBaseBinarySensor):
    """True if the device is currently locked (anti-theft).

    Reads ``lock_status`` from the device list (1 = locked, 2 = unlocked).
    Using ``BinarySensorDeviceClass.LOCK`` where HA convention is
    on = unlocked / off = locked.
    """

    _attr_device_class = BinarySensorDeviceClass.LOCK
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "Device Locked", "device_locked")

    @property
    def is_on(self) -> bool:
        # HA LOCK convention: is_on => unlocked
        return self.coordinator.data.get("lock_status") != 1
