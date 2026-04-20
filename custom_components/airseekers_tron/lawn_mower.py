"""Lawn mower platform for Airseekers Tron."""
import logging
from typing import Any

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STATE_IDLE, STATE_MOWING, STATE_PAUSED, STATE_CHARGING, STATE_DOCKING, STATE_OFFLINE
from .coordinator import AirseekersDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Airseekers lawn mower from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    coordinators = data["coordinators"]

    entities = []
    for sn, coordinator in coordinators.items():
        entities.append(AirseekersLawnMower(coordinator, api, sn))

    async_add_entities(entities)


class AirseekersLawnMower(CoordinatorEntity, LawnMowerEntity):
    """Representation of an Airseekers Tron lawn mower."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        LawnMowerEntityFeature.START_MOWING
        | LawnMowerEntityFeature.PAUSE
        | LawnMowerEntityFeature.DOCK
    )

    def __init__(
        self,
        coordinator: AirseekersDataCoordinator,
        api,
        sn: str,
    ) -> None:
        """Initialize the lawn mower."""
        super().__init__(coordinator)
        self._api = api
        self._sn = sn
        self._attr_unique_id = f"{sn}_mower"

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

    @property
    def activity(self) -> LawnMowerActivity:
        """Return the current activity."""
        state = self.coordinator.data.get("state", STATE_IDLE)
        
        if state == STATE_MOWING:
            return LawnMowerActivity.MOWING
        elif state == STATE_PAUSED:
            return LawnMowerActivity.PAUSED
        elif state in (STATE_DOCKING, STATE_CHARGING):
            return LawnMowerActivity.DOCKED
        elif state == STATE_OFFLINE:
            return LawnMowerActivity.ERROR
        else:
            return LawnMowerActivity.DOCKED

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.data.get("online", False)

    async def async_start_mowing(self) -> None:
        """Start mowing."""
        tasks = self.coordinator.data.get("tasks", [])
        if not tasks:
            _LOGGER.error("No scheduled tasks found - cannot start mowing. Create a task in the Airseekers mobile app first.")
            return
        task = tasks[0]  # Use first task
        await self._api.start_task(
            self._sn,
            task_id=task.get("id"),
            map_id=task.get("map_id"),
            mode=task.get("mode", 1),
            task_units=task.get("task_units"),
        )
        await self.coordinator.async_request_refresh()

    async def async_pause(self) -> None:
        """Pause mowing."""
        await self._api.pause_task(self._sn)
        await self.coordinator.async_request_refresh()

    async def async_dock(self) -> None:
        """Return to dock."""
        await self._api.dock(self._sn)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data
        device = data.get("device", {})
        notifications = data.get("notifications", [])
        
        attrs = {
            "serial_number": self._sn,
            "ip_address": data.get("ip_address"),
            "firmware_version": data.get("firmware_version"),
            "lock_status": data.get("lock_status"),
            "nrtk_bound": data.get("nrtk_bound"),
            "nrtk_available": data.get("nrtk_available"),
            "last_active": data.get("last_active"),
        }
        
        if notifications:
            attrs["last_notification"] = notifications[0].get("content")
            attrs["last_notification_time"] = notifications[0].get("created_at")
        
        return attrs
