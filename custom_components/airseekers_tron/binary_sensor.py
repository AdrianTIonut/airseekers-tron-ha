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
        """Initialize the sensor."""
        super().__init__(coordinator, sn, "Online", "online")

    @property
    def is_on(self) -> bool:
        """Return true if online."""
        return self.coordinator.data.get("online", False)


class AirseekersNrtkSensor(AirseekersBaseBinarySensor):
    """Binary sensor for NRTK (RTK) status."""

    _attr_icon = "mdi:satellite-variant"

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, sn, "RTK Available", "nrtk")

    @property
    def is_on(self) -> bool:
        """Return true if NRTK is available."""
        return self.coordinator.data.get("nrtk_available", False)

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        return {
            "nrtk_bound": self.coordinator.data.get("nrtk_bound"),
        }


class AirseekersOtaAvailableSensor(AirseekersBaseBinarySensor):
    """Binary sensor for firmware/MCU OTA availability."""

    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator, sn, "OTA Available", "ota_available")

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
        state = self.coordinator.data.get("state")
        return state == "charging"
