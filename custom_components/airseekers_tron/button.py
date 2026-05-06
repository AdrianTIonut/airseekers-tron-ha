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
            AirseekersRtkRebootButton(coordinator, api, sn),
            AirseekersCleanWarningsButton(coordinator, api, sn),
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
        """Handle the button press.

        Resolution order:
        1. **Legacy task pending** — pick up exactly where Tron left off
           after a dock cycle (uses ``legacy_task_id``).
        2. First scheduled task in the app.
        3. Fallback to the latest executed task (so users don't need a
           placeholder schedule in the app).
        """
        data = self.coordinator.data or {}
        has_legacy = bool(data.get("has_legacy_task"))
        legacy_id = data.get("legacy_task_id") or ""

        if has_legacy and legacy_id:
            tasks = data.get("tasks") or []
            base = tasks[0] if tasks else {}
            _LOGGER.info(
                "Start button: continuing legacy task %s", legacy_id,
            )
            await self._api.start_task(
                self._sn,
                task_id=legacy_id,
                map_id=data.get("current_map_id") or base.get("map_id"),
                mode=base.get("mode", 1),
                task_units=base.get("task_units"),
            )
            await self.coordinator.async_request_refresh()
            return

        task = None
        tasks = self.coordinator.data.get("tasks", [])
        if tasks:
            task = tasks[0]
        else:
            latest = await self._api.get_latest_task(self._sn)
            if latest and latest.get("task_units"):
                task = latest
                _LOGGER.info(
                    "Start button: no scheduled tasks; reusing latest "
                    "task %s (map %s)",
                    latest.get("id") or latest.get("task_id"),
                    latest.get("map_id"),
                )
            else:
                _LOGGER.error(
                    "Start button: no scheduled tasks and no recent task "
                    "on the device. Run the mower once from the Airseekers "
                    "app first."
                )
                return

        await self._api.start_task(
            self._sn,
            task_id=task.get("id") or task.get("task_id"),
            map_id=task.get("map_id"),
            mode=task.get("mode", 1),
            task_units=task.get("task_units"),
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
    """Button to resume mowing.

    Smart-resume that handles both cases:

    1. **Currently paused** (state=paused) — calls ``/task/resume`` which
       resumes the in-session paused task.
    2. **Legacy task pending** (e.g. Tron returned to dock for charging,
       task became "legacy", ``state=idle``, ``is_has_legacy_task=true``)
       — calls ``/task/start`` with ``task_id=<legacy_task_id>`` so Tron
       picks up exactly where it left off.

    The plain ``/task/resume`` endpoint silently does nothing for legacy
    tasks, which used to leave users stuck after a charge cycle.
    """

    def __init__(self, coordinator, api, sn: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator, api, sn, "Resume", "resume", "mdi:play-pause")

    async def async_press(self) -> None:
        """Handle the button press."""
        data = self.coordinator.data or {}
        has_legacy = bool(data.get("has_legacy_task"))
        legacy_id = data.get("legacy_task_id") or ""
        state = (data.get("state") or "").lower()

        # Legacy task takes priority — only happens after a dock cycle
        # with a half-done task. resume_task would silently no-op here.
        if has_legacy and legacy_id and state != "paused":
            tasks = data.get("tasks") or []
            base = tasks[0] if tasks else {}
            map_id = data.get("current_map_id") or base.get("map_id")
            mode = base.get("mode", 1)
            task_units = base.get("task_units")
            _LOGGER.info(
                "Resume button: starting legacy task %s (map %s)",
                legacy_id, map_id,
            )
            await self._api.start_task(
                self._sn,
                task_id=legacy_id,
                map_id=map_id,
                mode=mode,
                task_units=task_units,
            )
        else:
            _LOGGER.debug("Resume button: standard /task/resume")
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


class AirseekersRtkRebootButton(AirseekersBaseButton):
    """Button to reboot RTK base station."""

    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, api, sn: str) -> None:
        super().__init__(coordinator, api, sn, "Reboot RTK", "rtk_reboot", "mdi:restart")

    async def async_press(self) -> None:
        await self._api.rtk_reboot(self._sn)
        await self.coordinator.async_request_refresh()


class AirseekersCleanWarningsButton(AirseekersBaseButton):
    """Button to clear device warnings."""

    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, api, sn: str) -> None:
        super().__init__(coordinator, api, sn, "Clear Warnings", "clean_warn", "mdi:bell-off")

    async def async_press(self) -> None:
        await self._api.clean_warnings(self._sn)
        await self.coordinator.async_request_refresh()
