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
            AirseekersCutHeight(coordinator, api, sn),
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
    """Number entity for robot volume (0-100, %).

    The cloud's SetVolume field is on a 0-100 scale (verified via live
    state diff while dragging the volume slider in the official app).
    """

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator, api, sn,
            name="Volume",
            key="volume",
            icon="mdi:volume-high",
            min_value=0,
            max_value=100,
            step=1,
            unit="%",
        )

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.get("volume", 50)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self._api.set_volume(self._sn, int(value))
        await self.coordinator.async_request_refresh()


class AirseekersLightBrightness(AirseekersBaseNumber):
    """Number entity for robot light brightness (0-100 %).

    Granularity is per-1 (verified by observing slider drag in the
    official app — values like 18, 48, 52, 66 are all valid).
    """

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator, api, sn,
            name="Light Brightness",
            key="light_brightness",
            icon="mdi:brightness-6",
            min_value=0,
            max_value=100,
            step=1,
            unit="%",
        )

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.get("light_brightness", 0)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self._api.set_light_brightness(self._sn, int(value))
        await self.coordinator.async_request_refresh()


class AirseekersCutHeight(AirseekersBaseNumber):
    """Number entity for mowing cut height (20–120 mm, step 5 mm).

    Reads the current value from the first scheduled task's first
    task_unit (``cutter_height``).  When the user changes it, the full
    task is PUT back to the cloud via ``update_task_cut_height`` so the
    new height is saved and will be used on the next mow start.

    The entity is also read by ``start_mowing_advanced`` as the default
    height when the caller does not provide ``cut_height`` explicitly.
    """

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator, api, sn,
            name="Cut Height",
            key="cut_height",
            icon="mdi:grass",
            min_value=20,
            max_value=120,
            step=5,
            unit="mm",
        )

    @property
    def native_value(self) -> float | None:
        """Return cutter_height from the first scheduled task_unit."""
        tasks = (self.coordinator.data or {}).get("tasks") or []
        if not tasks:
            return None
        units = tasks[0].get("task_units") or []
        if not units:
            return None
        return units[0].get("cutter_height", 50)

    async def async_set_native_value(self, value: float) -> None:
        """Persist the new cut height to all task_units in the scheduled task."""
        tasks = (self.coordinator.data or {}).get("tasks") or []
        if not tasks:
            _LOGGER.error(
                "CutHeight: no scheduled task found — cannot persist height %s mm",
                int(value),
            )
            return
        ok = await self._api.update_task_cut_height(self._sn, tasks[0], int(value))
        if ok:
            await self.coordinator.async_request_refresh()
