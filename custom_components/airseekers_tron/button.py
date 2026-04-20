"""Button platform for Airseekers Tron."""
import logging

from homeassistant.components.button import ButtonEntity
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
    """Set up Airseekers buttons from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    coordinators = data["coordinators"]

    entities = []
    for sn, coordinator in coordinators.items():
        entities.extend([
            AirseekersStartButton(coordinator, api, sn),
            AirseekersStopButton(coordinator, api, sn),
            AirseekersPauseButton(coordinator, api, sn),
            AirseekersResumeButton(coordinator, api, sn),
            AirseekersDockButton(coordinator, api, sn),
        ])

    async_add_entities(entities)


class AirseekersBaseButton(CoordinatorEntity, ButtonEntity):
    """Base class for Airseekers buttons."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AirseekersDataCoordinator,
        api,
        sn: str,
        name: str,
        key: str,
        icon: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._api = api
        self._sn = sn
        self._attr_name = name
        self._attr_unique_id = f"{sn}_{key}"
        self._attr_icon = icon

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
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.data.get("online", False)


class AirseekersStartButton(AirseekersBaseButton):
    """Button to start mowing."""

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator, api, sn, "Start Mowing", "start", "mdi:play")

    async def async_press(self) -> None:
        """Handle the button press."""
        tasks = self.coordinator.data.get("tasks", [])
        if not tasks:
            _LOGGER.error(
                "No scheduled tasks found - cannot start mowing. "
                "Create a task in the Airseekers mobile app first."
            )
            return
        task = tasks[0]
        await self._api.start_task(
            self._sn,
            task_id=task.get("id"),
            map_id=task.get("map_id"),
            mode=task.get("mode", 1),
        )
        await self.coordinator.async_request_refresh()


class AirseekersStopButton(AirseekersBaseButton):
    """Button to stop mowing."""

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator, api, sn, "Stop", "stop", "mdi:stop")

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.stop_task(self._sn)
        await self.coordinator.async_request_refresh()


class AirseekersPauseButton(AirseekersBaseButton):
    """Button to pause mowing."""

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator, api, sn, "Pause", "pause", "mdi:pause")

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.pause_task(self._sn)
        await self.coordinator.async_request_refresh()


class AirseekersResumeButton(AirseekersBaseButton):
    """Button to resume mowing."""

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator, api, sn, "Resume", "resume", "mdi:play-pause")

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.resume_task(self._sn)
        await self.coordinator.async_request_refresh()


class AirseekersDockButton(AirseekersBaseButton):
    """Button to return to dock."""

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator, api, sn, "Return to Dock", "dock", "mdi:home")

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.dock(self._sn)
        await self.coordinator.async_request_refresh()
