"""Select platform for Airseekers Tron."""
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MOWING_MODES
from .coordinator import AirseekersDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Airseekers select entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    coordinators = data["coordinators"]

    entities = []
    for sn, coordinator in coordinators.items():
        entities.append(AirseekersMowingModeSelect(coordinator, api, sn))

    async_add_entities(entities)


class AirseekersMowingModeSelect(CoordinatorEntity, SelectEntity):
    """Select entity for mowing mode."""

    _attr_has_entity_name = True
    _attr_name = "Mowing Mode"
    _attr_icon = "mdi:robot-mower"
    _attr_options = [
        "AI Mowing",
        "Global Mowing",
        "Edge Mowing",
        "Area Mowing",
        "Manual Mode",
        "Remote Control",
    ]

    def __init__(
        self,
        coordinator: AirseekersDataCoordinator,
        api,
        sn: str,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._api = api
        self._sn = sn
        self._attr_unique_id = f"{sn}_mowing_mode"

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

    @property
    def current_option(self) -> str:
        """Return the current option."""
        mode = self.coordinator.data.get("mowing_mode", "global_mowing")
        mode_map = {
            "ai_mowing": "AI Mowing",
            "global_mowing": "Global Mowing",
            "edge_mowing": "Edge Mowing",
            "area_mowing": "Area Mowing",
            "manual_mode": "Manual Mode",
            "remote_control_mode": "Remote Control",
        }
        return mode_map.get(mode, "Global Mowing")

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        mode_map = {
            "AI Mowing": "ai_mowing",
            "Global Mowing": "global_mowing",
            "Edge Mowing": "edge_mowing",
            "Area Mowing": "area_mowing",
            "Manual Mode": "manual_mode",
            "Remote Control": "remote_control_mode",
        }
        mode = mode_map.get(option, "global_mowing")
        _LOGGER.info(f"Setting mowing mode to {mode} for {self._sn}")
        # TODO: Implement when endpoint is discovered
        await self.coordinator.async_request_refresh()
