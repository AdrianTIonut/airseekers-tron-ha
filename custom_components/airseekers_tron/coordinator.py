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
            # Device list (always needed for online status, func_list)
            devices = await self.api.get_devices()
            device = next(
                (d for d in devices if d.get("sn") == self.device_sn), None
            )

            if not device:
                raise UpdateFailed(f"Device {self.device_sn} not found")

            # Full status - THE source of truth for real-time state
            full_status = await self.api.get_full_status(self.device_sn)

            # Config (for volume, night mode, etc - these are stored server-side)
            config = await self.api.get_device_config(self.device_sn)

            # Lightweight recent notifications (for last notification sensor)
            notifications = await self.api.get_notifications(self.device_sn, size=5)

            # Scheduled tasks (needed for start_task to have task_id/map_id/task_units)
            tasks = await self.api.get_device_tasks(self.device_sn)

            # Maps (for map switcher)
            maps = await self.api.get_device_map(self.device_sn)

            # Task history (for statistics)
            history = await self.api.get_task_history(self.device_sn, size=5)

            # Determine state - uses full_status as primary, notifications as fallback
            state = self.api.determine_state(device, notifications, full_status)

            # Night mode parsing
            night_mode_raw = config.get("SetDarkMode", "22:00-06:00")
            night_mode_parts = night_mode_raw.split("-")
            night_mode_start = night_mode_parts[0] if len(night_mode_parts) == 2 else "22:00"
            night_mode_end = night_mode_parts[1] if len(night_mode_parts) == 2 else "06:00"

            # Helpers to safely extract nested data from full_status
            battery = full_status.get("battery_status") or {}
            task_status = full_status.get("task_status") or {}
            rtk_status = full_status.get("rtk_status") or {}
            rtk_info = full_status.get("rtk_info") or {}
            net_info = full_status.get("net_info") or {}
            version = full_status.get("version") or {}
            sensor_status = full_status.get("sensor_status") or {}
            upgrade_status = full_status.get("upgrade_status") or {}
            upgrade_mcu = full_status.get("upgrade_mcu_status") or {}

            return {
                # Raw payloads (for entities that need full access)
                "device": device,
                "config": config,
                "full_status": full_status,
                "state": state,
                "notifications": notifications,
                "tasks": tasks,
                "maps": maps,
                "history": history,
                # Device basics (from /device list)
                "online": device.get("online_status") == 1,
                "firmware_version": device.get("firmware_ver"),
                "ip_address": device.get("ip"),
                "lock_status": device.get("lock_status"),
                "nrtk_bound": device.get("nrtk_bound"),
                "nrtk_available": device.get("nrtk_available"),
                "last_active": device.get("latest_active_time"),
                "iccid": device.get("iccid"),
                "func_list": device.get("func_list", []),
                # Config (stored server-side)
                "volume": int(config.get("SetVolume", "5") or "5"),
                "light_brightness": int(config.get("SetLightBrightness", "0") or "0"),
                "night_mode_enabled": True,
                "night_mode_start": night_mode_start,
                "night_mode_end": night_mode_end,
                "device_lock": config.get("DeviceLock", "0") == "1",
                "enable_nrtk": config.get("EnableNRTK", "0") == "1",
                "upload_4g": config.get("Net4GAllowUploadPicture", "1") == "1",
                # Battery (from full_status)
                "battery_percentage": battery.get("battery_percentage"),
                "battery_temperature": battery.get("battery_temperature"),
                "battery_error": battery.get("battery_error"),
                # Task status live
                "task_state": task_status.get("state"),
                "current_task_id": task_status.get("task_id"),
                "current_map_id": task_status.get("map_id"),
                "run_time": task_status.get("run_time"),
                "task_start_time": task_status.get("start_time"),
                "remaining_area": task_status.get("remaining_area"),
                "current_total_area": task_status.get("total_area"),
                "has_legacy_task": task_status.get("is_has_legacy_task", False),
                # Position / RTK live
                "robot_lat": rtk_status.get("robot_pose_lat"),
                "robot_lon": rtk_status.get("robot_pose_lon"),
                "robot_x": rtk_status.get("robot_pose_x"),
                "robot_y": rtk_status.get("robot_pose_y"),
                "robot_yaw": rtk_status.get("robot_pose_yaw"),
                "rtk_quality_state": rtk_status.get("rtk_status"),
                "num_satellites": rtk_status.get("num_satellites"),
                "num_satellites_used": rtk_status.get("num_satellites_used"),
                "lora_rssi": rtk_status.get("lora_rssi_dbm"),
                "localization_state": rtk_status.get("localization_state"),
                "ref_station_state": rtk_status.get("ref_station_state"),
                "rtk_snr": rtk_info.get("rtk_snr"),
                "rtk_num": rtk_info.get("rtk_num"),
                # Network
                "wifi_ssid": net_info.get("wifi_ssid"),
                "wifi_dbm": net_info.get("wifi_dbm"),
                "wifi_ip": net_info.get("wifi_ip"),
                "wireless_4g_ip": net_info.get("wireless_4g_ip"),
                "sim_active": net_info.get("sim_active") == 1,
                "net_info_type": net_info.get("net_info_type"),
                # Versions (detailed)
                "chassis_board": version.get("chassis_board"),
                "cutter_board": version.get("cutter_board"),
                "rtk_board": version.get("rtk_board"),
                "mower_package": version.get("mower_package"),
                "voice_language": version.get("voice_language"),
                "voice_version": version.get("voice_version"),
                # Upgrade indicators
                "firmware_upgrade_progress": upgrade_status.get("progress"),
                "firmware_upgrade_state": upgrade_status.get("state"),
                "mcu_current_version": upgrade_mcu.get("current_version"),
                "mcu_target_version": upgrade_mcu.get("target_version"),
                "mcu_upgrade_available": (
                    upgrade_mcu.get("current_version")
                    and upgrade_mcu.get("target_version")
                    and upgrade_mcu.get("current_version") != upgrade_mcu.get("target_version")
                ),
                # Statistics (from history)
                "total_mowed_area": history.get("summary", {}).get("total_area", 0),
                "total_mowing_time": history.get("summary", {}).get("total_duration", 0),
                "total_task_count": history.get("summary", {}).get("total_count", 0),
            }

        except AirseekersApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
