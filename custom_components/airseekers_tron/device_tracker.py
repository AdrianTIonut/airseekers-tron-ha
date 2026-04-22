"""Device tracker platform for Airseekers Tron (GPS position)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AirseekersDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the mower location tracker from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinators = data["coordinators"]

    entities = [
        AirseekersLocationTracker(coordinator, sn)
        for sn, coordinator in coordinators.items()
    ]
    async_add_entities(entities)


class AirseekersLocationTracker(CoordinatorEntity, TrackerEntity):
    """Tracks the mower's GPS position from full_status.rtk_status.robot_pose_lat/lon.

    Appears on the HA map, so zone automations (e.g. "mower left geofence")
    work out of the box.
    """

    _attr_has_entity_name = True
    _attr_name = "Location"
    _attr_icon = "mdi:map-marker"

    def __init__(self, coordinator: AirseekersDataCoordinator, sn: str) -> None:
        super().__init__(coordinator)
        self._sn = sn
        self._attr_unique_id = f"{sn}_location"

    @property
    def device_info(self) -> dict[str, Any]:
        device = self.coordinator.data.get("device", {})
        return {
            "identifiers": {(DOMAIN, self._sn)},
            "name": f"Airseekers Tron {self._sn[-6:]}",
            "manufacturer": "Airseekers",
            "model": "Tron",
            "sw_version": device.get("firmware_ver"),
        }

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        value = self.coordinator.data.get("robot_lat")
        if isinstance(value, (int, float)) and value != 0:
            return float(value)
        return None

    @property
    def longitude(self) -> float | None:
        value = self.coordinator.data.get("robot_lon")
        if isinstance(value, (int, float)) and value != 0:
            return float(value)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose raw pose + RTK fix quality as attributes."""
        data = self.coordinator.data
        return {
            "serial_number": self._sn,
            "altitude": data.get("robot_altitude"),
            "pose_x": data.get("robot_x"),
            "pose_y": data.get("robot_y"),
            "pose_yaw": data.get("robot_yaw"),
            "rtk_fix": data.get("rtk_quality_state"),
            "localization_state": data.get("localization_state"),
            "num_satellites": data.get("num_satellites"),
        }
