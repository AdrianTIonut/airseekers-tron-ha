"""Data coordinator for Airseekers Tron."""
import asyncio
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

            # NEW: warranty, NRTK availability, voice pack update, last task record,
            # latest firmware. Fetched in parallel to minimise round trips; each
            # endpoint returns {} on error.
            (
                warranty,
                ext_warranty,
                nrtk_supported,
                voice_info,
                last_task,
                firmware_latest,
            ) = await asyncio.gather(
                self.api.get_warranty(self.device_sn),
                self.api.get_extended_warranty(self.device_sn),
                self.api.get_nrtk_supported(self.device_sn),
                self.api.get_voice_version(self.device_sn),
                self.api.get_task_record_latest(self.device_sn),
                self.api.get_firmware_latest(self.device_sn),
                return_exceptions=False,
            )

            # Determine state - uses full_status as primary, notifications as fallback
            state = self.api.determine_state(device, notifications, full_status)

            # Night mode parsing — empty SetDarkMode means OFF (verified
            # by toggling Night Mode in the official app and watching the
            # cloud `SetDarkMode` go from "22:00-06:55" to "").
            night_mode_raw = (config.get("SetDarkMode") or "").strip()
            night_mode_enabled = bool(night_mode_raw)
            if night_mode_enabled and "-" in night_mode_raw:
                parts = night_mode_raw.split("-", 1)
                night_mode_start = parts[0] or "22:00"
                night_mode_end = parts[1] or "06:00"
            else:
                # Defaults shown in HA when night mode is off
                night_mode_start = "22:00"
                night_mode_end = "06:00"

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
            upgrade_voice = full_status.get("voice_upgrade_status") or {}
            explore_info = full_status.get("explore_mapping_info") or {}
            nrtk_info = device.get("nrtk_info") or {}

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
                "volume": int(config.get("SetVolume", "50") or "50"),
                "light_brightness": int(config.get("SetLightBrightness", "0") or "0"),
                "night_mode_enabled": night_mode_enabled,
                "night_mode_raw": night_mode_raw,
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
                # ------------------------------------------------------------------
                # NEW in this version — previously discovered via APK dump but
                # never surfaced as entities.
                # ------------------------------------------------------------------
                # Task status extras
                "task_type": task_status.get("type"),
                "task_update_time": task_status.get("update_time"),
                # RTK extras (rtk_info from full_status — separate from rtk/address-info)
                "rtk_version": rtk_info.get("rtk_version"),
                "rtk_base_sn": rtk_info.get("rtk_sn"),
                "rtk_channel_current": rtk_info.get("rtk_channel"),
                "rtk_addr_current": rtk_info.get("rtk_addr"),
                # Altitude (rtk_status)
                "robot_altitude": rtk_status.get("robot_pose_altitude"),
                # Sensor status raw (bitfield)
                "sensor_status_raw": sensor_status.get("status"),
                # Firmware/MCU/voice OTA status
                "mcu_upgrade_progress": upgrade_mcu.get("progress"),
                "mcu_upgrade_state": upgrade_mcu.get("state"),
                "mcu_upgrade_step": upgrade_mcu.get("step"),
                "mcu_upgrade_type": upgrade_mcu.get("type"),
                "voice_upgrade_progress": upgrade_voice.get("progress"),
                "voice_upgrade_state": upgrade_voice.get("state"),
                "voice_upgrade_step": upgrade_voice.get("step"),
                # Explore / mapping session
                "explore_state": explore_info.get("state"),
                "explore_boundary_poses": explore_info.get("boundary_pose_size"),
                "explore_trajectory_poses": explore_info.get("trajectory_pose_size"),
                # NRTK subscription details (from device list)
                "nrtk_bind_type": nrtk_info.get("bind_type"),
                "nrtk_active_status": nrtk_info.get("active_status"),
                "nrtk_trial_available": nrtk_info.get("trial_available"),
                "nrtk_trial_duration": nrtk_info.get("trial_duration"),
                "nrtk_trial_remaining": nrtk_info.get("trial_remaining_time"),
                "timezone_offset": device.get("timezone_offset"),
                # Warranty (new endpoints)
                "warranty_start": warranty.get("start_at"),
                "warranty_end": warranty.get("end_at"),
                "has_extended_warranty": bool(ext_warranty),
                "extended_warranty_start": ext_warranty.get("start_at") if ext_warranty else None,
                "extended_warranty_end": ext_warranty.get("end_at") if ext_warranty else None,
                # NRTK supported (location-based)
                "nrtk_area_supported": bool(nrtk_supported.get("available"))
                    if isinstance(nrtk_supported, dict) else False,
                # Voice pack upgrade
                "voice_current_version": voice_info.get("current_version"),
                "voice_new_version": voice_info.get("new_version"),
                "voice_upgradable": bool(voice_info.get("upgradable")),
                "voice_change_log": voice_info.get("change_log"),
                "last_task_record": last_task if isinstance(last_task, dict) and last_task.get("id") else None,
                # Latest firmware (from /firmware/latest). Code 407 = already latest.
                "firmware_latest_version": firmware_latest.get("version"),
                "firmware_current_version": firmware_latest.get("current_version"),
                "firmware_upgradable": bool(firmware_latest.get("upgradable")),
                "firmware_force_upgrade": bool(firmware_latest.get("force_upgrade")),
                "firmware_change_log": firmware_latest.get("change_log") or "",
                # Legacy task awaiting resume (task_status)
                "legacy_task_id": task_status.get("legacy_task_id") or "",
                # WiFi IP (separate from 4G)
                "wifi_ip": net_info.get("wifi_ip") or "",
                # RTK addr/channel currently in use
                "rtk_addr_active": rtk_info.get("rtk_addr"),
                "rtk_channel_active": rtk_info.get("rtk_channel"),
                "rtk_quality_numeric": rtk_info.get("rtk_quality"),
                # Upgrade status step (already have progress/state)
                "firmware_upgrade_step": upgrade_status.get("step"),
            }

        except AirseekersApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
