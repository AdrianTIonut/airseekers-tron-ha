"""Data coordinator for Airseekers Tron."""
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AirseekersApi, AirseekersApiError
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AirseekersDataCoordinator(DataUpdateCoordinator):
    """Airseekers data update coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AirseekersApi,
        device_sn: str,
        update_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_sn}",
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.device_sn = device_sn

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API."""
        try:
            # Get device info
            devices = await self.api.get_devices()
            device = next(
                (d for d in devices if d.get("sn") == self.device_sn),
                None
            )
            
            if not device:
                raise UpdateFailed(f"Device {self.device_sn} not found")

            # Get config (volume, light, night mode)
            config = await self.api.get_device_config(self.device_sn)

            # Get notifications
            notifications = await self.api.get_notifications(self.device_sn, size=5)
            
            # Get tasks
            tasks = await self.api.get_device_tasks(self.device_sn)
            
            # Get maps
            maps = await self.api.get_device_map(self.device_sn)

            # Get task history
            history = await self.api.get_task_history(self.device_sn, size=5)
            
            # Determine state
            state = self.api.determine_state(device, notifications)

            # Parse night mode
            night_mode_raw = config.get("SetDarkMode", "22:00-06:00")
            night_mode_parts = night_mode_raw.split("-")
            night_mode_start = night_mode_parts[0] if len(night_mode_parts) == 2 else "22:00"
            night_mode_end = night_mode_parts[1] if len(night_mode_parts) == 2 else "06:00"

            return {
                "device": device,
                "config": config,
                "state": state,
                "notifications": notifications,
                "tasks": tasks,
                "maps": maps,
                "history": history,
                # Device info
                "online": device.get("online_status") == 1,
                "firmware_version": device.get("firmware_ver"),
                "ip_address": device.get("ip"),
                "lock_status": device.get("lock_status"),
                "nrtk_bound": device.get("nrtk_bound"),
                "nrtk_available": device.get("nrtk_available"),
                "last_active": device.get("latest_active_time"),
                "iccid": device.get("iccid"),
                "func_list": device.get("func_list", []),
                # Config values
                "volume": int(config.get("SetVolume", "5")),
                "light_brightness": int(config.get("SetLightBrightness", "0")),
                "night_mode_enabled": True,  # Always enabled, controlled by schedule
                "night_mode_start": night_mode_start,
                "night_mode_end": night_mode_end,
                "device_lock": config.get("DeviceLock", "0") == "1",
                "enable_nrtk": config.get("EnableNRTK", "0") == "1",
                "upload_4g": config.get("Net4GAllowUploadPicture", "1") == "1",
                # Statistics
                "total_mowed_area": history.get("summary", {}).get("total_area", 0),
                "total_mowing_time": history.get("summary", {}).get("total_duration", 0),
                "total_task_count": history.get("summary", {}).get("total_count", 0),
            }

        except AirseekersApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
