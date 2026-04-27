"""Switch platform for Airseekers Tron."""
import logging

from homeassistant.components.switch import SwitchEntity
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
    """Set up Airseekers switches from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    coordinators = data["coordinators"]

    entities = []
    for sn, coordinator in coordinators.items():
        entities.extend([
            AirseekersNightModeSwitch(coordinator, api, sn),
            AirseekersLockModeSwitch(coordinator, api, sn),
        ])

    async_add_entities(entities)


class AirseekersBaseSwitch(CoordinatorEntity, SwitchEntity):
    """Base class for Airseekers switches."""

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
        """Initialize the switch."""
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


class AirseekersNightModeSwitch(AirseekersBaseSwitch):
    """Switch for night mode."""

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the switch."""
        super().__init__(
            coordinator, api, sn,
            name="Night Mode",
            key="night_mode",
            icon="mdi:weather-night"
        )

    @property
    def is_on(self) -> bool:
        """Return true if night mode is on."""
        return self.coordinator.data.get("night_mode_enabled", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on night mode.

        Night mode is governed by SetDarkMode = "HH:MM-HH:MM". An empty
        value disables it, a range enables it. We restore whatever the
        user last had (if known), otherwise apply a sensible default.
        """
        previous = self.coordinator.data.get("night_mode_raw") or ""
        # If we have a previous schedule remembered, reuse it. Otherwise
        # fall back to start/end values stored in coordinator data, then
        # to a sensible default of 22:00-06:00.
        start = self.coordinator.data.get("night_mode_start") or "22:00"
        end = self.coordinator.data.get("night_mode_end") or "06:00"
        schedule = previous if previous else f"{start}-{end}"
        _LOGGER.info("Enabling night mode (%s) for %s", schedule, self._sn)
        await self._api.set_config(self._sn, "SetDarkMode", schedule)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off night mode by clearing SetDarkMode."""
        _LOGGER.info("Disabling night mode for %s", self._sn)
        await self._api.set_config(self._sn, "SetDarkMode", "")
        await self.coordinator.async_request_refresh()


class AirseekersLockModeSwitch(AirseekersBaseSwitch):
    """Switch for lock/anti-theft mode."""

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the switch."""
        super().__init__(
            coordinator, api, sn,
            name="Lock Mode",
            key="lock_mode",
            icon="mdi:lock"
        )

    @property
    def is_on(self) -> bool:
        """Return true if lock mode is on."""
        return self.coordinator.data.get("lock_status", 0) == 1

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on lock mode."""
        _LOGGER.info(f"Locking robot {self._sn}")
        # Lock requires a password - this would need to be configured
        # await self._api.lock(self._sn, "1234")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off lock mode."""
        _LOGGER.info(f"Unlocking robot {self._sn}")
        # await self._api.unlock(self._sn, "1234")
        await self.coordinator.async_request_refresh()
