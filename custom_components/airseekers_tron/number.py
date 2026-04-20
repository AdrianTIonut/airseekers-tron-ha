"""Number platform for Airseekers Tron."""
import logging

from homeassistant.components.number import NumberEntity, NumberMode
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
    """Set up Airseekers number entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    coordinators = data["coordinators"]

    entities = []
    for sn, coordinator in coordinators.items():
        entities.extend([
            AirseekersVolume(coordinator, api, sn),
            AirseekersLightBrightness(coordinator, api, sn),
        ])

    async_add_entities(entities)


class AirseekersBaseNumber(CoordinatorEntity, NumberEntity):
    """Base class for Airseekers number entities."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: AirseekersDataCoordinator,
        api,
        sn: str,
        name: str,
        key: str,
        icon: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str = None,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._api = api
        self._sn = sn
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{sn}_{key}"
        self._attr_icon = icon
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        if unit:
            self._attr_native_unit_of_measurement = unit

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


class AirseekersVolume(AirseekersBaseNumber):
    """Number entity for robot volume (0-10)."""

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator, api, sn,
            name="Volume",
            key="volume",
            icon="mdi:volume-high",
            min_value=0,
            max_value=10,
            step=1,
        )

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.get("volume", 5)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self._api.set_volume(self._sn, int(value))
        await self.coordinator.async_request_refresh()


class AirseekersLightBrightness(AirseekersBaseNumber):
    """Number entity for robot light brightness (0-100)."""

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator, api, sn,
            name="Light Brightness",
            key="light_brightness",
            icon="mdi:brightness-6",
            min_value=0,
            max_value=100,
            step=10,
            unit="%"
        )

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.get("light_brightness", 0)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self._api.set_light_brightness(self._sn, int(value))
        await self.coordinator.async_request_refresh()
