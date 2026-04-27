"""Airseekers Tron API Client."""
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .const import (
    API_BASE_URL,
    API_LOGIN,
    API_DEVICES,
    API_TASK,
    API_TASK_START,
    API_TASK_STOP,
    API_TASK_PAUSE,
    API_TASK_RESUME,
    API_TASK_DOCK,
    API_DEVICE_MAP,
    API_DEVICE_LOCK,
    API_DEVICE_UNLOCK,
    API_NOTIFY_LIST,
    API_FIRMWARE,
    API_RTK_INFO,
    API_TASK_RECORD,
    API_WARRANTY,
    API_EXTENDED_WARRANTY,
    API_NRTK_SUPPORTED,
    API_VOICE_VERSION,
    API_TASK_LATEST,
    STATE_IDLE,
    STATE_MOWING,
    STATE_PAUSED,
    STATE_DOCKING,
    STATE_CHARGING,
    STATE_OFFLINE,
)

_LOGGER = logging.getLogger(__name__)

# Additional API endpoints
API_CONFIG = "/api/web/device/config"
API_TASK_RECORD_LIST = "/api/web/device/task-record/list"


class AirseekersApiError(Exception):
    """Exception for API errors."""
    pass


class AirseekersAuthError(AirseekersApiError):
    """Exception for authentication errors."""
    pass


class AirseekersApi:
    """Airseekers Tron API Client."""

    def __init__(self, email: str, password: str) -> None:
        """Initialize the API client."""
        self._email = email
        self._password = password
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        # Lock to prevent multiple parallel re-login attempts
        self._relogin_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _is_auth_error(self, status: int, data: dict) -> bool:
        """Detect authentication errors from HTTP status or response body."""
        if status == 401:
            return True
        if data.get("code", 0) != 0:
            msg = data.get("msg", "").lower()
            return any(
                kw in msg
                for kw in ("illegal", "credential", "token", "unauthorized", "login")
            )
        return False

    async def _relogin(self) -> None:
        """Re-login, protected by lock to prevent concurrent attempts."""
        async with self._relogin_lock:
            _LOGGER.warning("Token invalid, performing re-login...")
            self._access_token = None
            await self.login()

    async def login(self) -> bool:
        """Login to Airseekers API."""
        session = await self._get_session()
        url = f"{API_BASE_URL}{API_LOGIN}"
        payload = {"email": self._email, "password": self._password}

        try:
            async with session.post(
                url, json=payload, headers={"Content-Type": "application/json"}
            ) as resp:
                data = await resp.json()

                if data.get("code") != 0:
                    raise AirseekersAuthError(
                        f"Login failed: {data.get('msg', 'Unknown error')}"
                    )

                self._access_token = data["data"]["access_token"]
                self._refresh_token = data["data"].get("refresh_token")

                _LOGGER.debug("Successfully logged in to Airseekers API")
                return True

        except aiohttp.ClientError as err:
            raise AirseekersApiError(f"Connection error: {err}") from err

    async def _get(self, path: str, params: dict = None) -> dict:
        """GET request with automatic re-login on auth error."""
        if not self._access_token:
            await self.login()

        session = await self._get_session()
        url = f"{API_BASE_URL}{path}"

        try:
            async with session.get(url, params=params, headers=self._headers()) as resp:
                data = await resp.json()
                if self._is_auth_error(resp.status, data):
                    await self._relogin()
                    # Retry once with new token
                    async with session.get(
                        url, params=params, headers=self._headers()
                    ) as retry:
                        data = await retry.json()
                        if self._is_auth_error(retry.status, data):
                            raise AirseekersAuthError(
                                "Re-login failed, credentials may be invalid"
                            )
                return data
        except aiohttp.ClientError as err:
            raise AirseekersApiError(f"Connection error: {err}") from err

    async def _post(self, path: str, payload: dict) -> dict:
        """POST request with automatic re-login on auth error."""
        if not self._access_token:
            await self.login()

        session = await self._get_session()
        url = f"{API_BASE_URL}{path}"

        try:
            async with session.post(url, json=payload, headers=self._headers()) as resp:
                data = await resp.json()
                if self._is_auth_error(resp.status, data):
                    await self._relogin()
                    # Retry once with new token
                    async with session.post(
                        url, json=payload, headers=self._headers()
                    ) as retry:
                        data = await retry.json()
                        if self._is_auth_error(retry.status, data):
                            raise AirseekersAuthError(
                                "Re-login failed, credentials may be invalid"
                            )
                return data
        except aiohttp.ClientError as err:
            raise AirseekersApiError(f"Connection error: {err}") from err

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get list of devices."""
        data = await self._get(API_DEVICES)
        if data.get("code") != 0:
            raise AirseekersApiError(f"Failed to get devices: {data.get('msg')}")
        return data.get("data", {}).get("list", [])

    async def get_device_config(self, sn: str) -> Dict[str, Any]:
        """Get device configuration (volume, light, night mode, etc)."""
        data = await self._get(API_CONFIG, params={"sn": sn})
        if data.get("code") != 0:
            return {}
        return data.get("data", {}).get("configs", {})

    async def set_config(self, sn: str, key: str, value: str) -> bool:
        """Set a configuration value.

        The cloud accepts a flat ``{"sn": ..., "key": value}`` body and
        responds with ``code: 0`` (success), but **silently drops** the
        write — the field never persists. The only body shape that
        actually saves is the wrapped form below, verified by writing a
        unique value and reading it back through ``GET /config``::

            {"sn": "...", "configs": {"<Key>": "<value>"}}

        See ``probe_config_format.py`` in the repo for the test harness
        that uncovered this.
        """
        data = await self._post(API_CONFIG, {"sn": sn, "configs": {key: value}})
        if data.get("code") == 0:
            _LOGGER.info("Config %s=%s set successfully for %s", key, value, sn)
            return True
        _LOGGER.error("Failed to set config: %s", data.get("msg"))
        return False

    async def set_volume(self, sn: str, volume: int) -> bool:
        """Set robot volume (0-100).

        Discovered via live cloud-state diff: the app's volume slider sends
        values 0..100 to /api/web/device/config under the `SetVolume` key
        (stored as a string). Earlier integration versions clamped to 0-10
        by mistake — that maps to 7 = 7% which is barely audible.
        """
        return await self.set_config(sn, "SetVolume", str(max(0, min(100, int(volume)))))

    async def set_light_brightness(self, sn: str, brightness: int) -> bool:
        """Set light brightness (0-100).

        The app fires two requests when the slider moves: one to
        `/api/web/device/config` (SetLightBrightness, cloud-side state)
        and one to `/api/web/device/fill-light-setting` (real-time push
        to the robot). We do both so the cloud value stays in sync with
        what the device actually does.
        """
        brightness = max(0, min(100, int(brightness)))
        # Cloud-side config (what the app shows on next open)
        await self.set_config(sn, "SetLightBrightness", str(brightness))
        # Real-time push to the device
        return await self.set_fill_light(sn, brightness, enabled=brightness > 0)

    async def set_night_mode(self, sn: str, start_time: str, end_time: str) -> bool:
        """Set night mode schedule (HH:MM-HH:MM)."""
        return await self.set_config(sn, "SetDarkMode", f"{start_time}-{end_time}")

    async def set_4g_upload(self, sn: str, enabled: bool) -> bool:
        """Enable/disable 4G picture upload."""
        return await self.set_config(
            sn, "Net4GAllowUploadPicture", "1" if enabled else "0"
        )

    async def get_device_tasks(self, sn: str) -> List[Dict[str, Any]]:
        """Get device scheduled tasks."""
        data = await self._get(API_TASK, params={"sn": sn})
        if data.get("code") != 0:
            return []
        return data.get("data", {}).get("list", [])

    async def get_latest_task(self, sn: str) -> Dict[str, Any]:
        """Get the most recent task definition (used by app's Quick Mow).

        Returns the last task that was executed with its full definition:
        task_id, map_id, mode, task_units. We use this as a fallback when no
        scheduled tasks exist, so HA can replay the user's last manual start
        without requiring a placeholder schedule in the app.
        """
        data = await self._get(API_TASK_LATEST, params={"sn": sn})
        if data.get("code") != 0:
            return {}
        return data.get("data", {}) or {}

    async def get_task_history(
        self, sn: str, page: int = 1, size: int = 10
    ) -> Dict[str, Any]:
        """Get task history with statistics."""
        data = await self._get(
            API_TASK_RECORD_LIST, params={"sn": sn, "page": page, "size": size}
        )
        if data.get("code") != 0:
            return {}
        return data.get("data", {})

    async def get_notifications(
        self, sn: str, page: int = 1, size: int = 10
    ) -> List[Dict[str, Any]]:
        """Get device notifications."""
        data = await self._get(
            API_NOTIFY_LIST, params={"sn": sn, "page": page, "size": size}
        )
        if data.get("code") != 0:
            return []
        return data.get("data", {}).get("list", [])

    async def get_device_map(self, sn: str) -> List[Dict[str, Any]]:
        """Get device maps."""
        data = await self._get(API_DEVICE_MAP, params={"sn": sn})
        if data.get("code") != 0:
            return []
        return data.get("data", [])

    async def get_rtk_info(self, sn: str) -> Dict[str, Any]:
        """Get RTK information."""
        data = await self._get(API_RTK_INFO, params={"sn": sn})
        return data.get("data", {})

    async def get_full_status(self, sn: str) -> Dict[str, Any]:
        """Get full device status (battery, task, position, RTK, network, versions).

        This is the KEY endpoint for real-time state. Returns nested dicts:
        - battery_status: battery_percentage, battery_temperature, battery_error
        - task_status: state, task_id, map_id, run_time, remaining_area, total_area
        - rtk_status: localization_state, robot_pose_lat/lon/yaw, num_satellites, rtk_status
        - rtk_info: rtk_snr, rtk_quality, rtk_version
        - net_info: wifi_ssid, wifi_dbm, wireless_4g_ip, sim_active
        - sensor_status, online_status
        - version: chassis_board, cutter_board, rtk_board, mower_package, voice_version
        - upgrade_status, upgrade_mcu_status, voice_upgrade_status
        """
        data = await self._get("/api/web/device/full-status", params={"sn": sn})
        if data.get("code") != 0:
            return {}
        return data.get("data", {}) or {}

    async def get_warranty(self, sn: str) -> Dict[str, Any]:
        """Get device warranty info (start/end epoch). Returns {} on error."""
        data = await self._get(API_WARRANTY, params={"sn": sn})
        if data.get("code") != 0:
            return {}
        return data.get("data", {}) or {}

    async def get_extended_warranty(self, sn: str) -> Dict[str, Any]:
        """Get extended warranty info. Returns {} if not purchased (code 701)."""
        data = await self._get(API_EXTENDED_WARRANTY, params={"sn": sn})
        if data.get("code") != 0:
            return {}
        return data.get("data", {}) or {}

    async def get_nrtk_supported(self, sn: str) -> Dict[str, Any]:
        """Check if NRTK is available at the device's location."""
        data = await self._get(API_NRTK_SUPPORTED, params={"sn": sn})
        if data.get("code") != 0:
            return {}
        return data.get("data", {}) or {}

    async def get_voice_version(self, sn: str) -> Dict[str, Any]:
        """Get voice pack version info (current, latest, upgradable)."""
        data = await self._get(API_VOICE_VERSION, params={"sn": sn})
        if data.get("code") != 0:
            return {}
        return data.get("data", {}) or {}

    async def get_task_record_latest(self, sn: str) -> Dict[str, Any]:
        """Get the most recent completed task record (with pictures/duration/area)."""
        data = await self._get(API_TASK_RECORD, params={"sn": sn})
        if data.get("code") != 0:
            return {}
        return data.get("data", {}) or {}

    async def get_firmware_latest(self, sn: str) -> Dict[str, Any]:
        """Get latest firmware metadata.

        Returns a dict with at least ``version``, ``current_version`` and
        ``upgradable``. The API replies with code 407 ("Already the latest
        version") when there is no upgrade — we still return ``data`` in that
        case so the caller can surface the current/target version.
        """
        data = await self._get(API_FIRMWARE, params={"sn": sn})
        # code 407 is "already latest" — the payload is still useful.
        if data.get("code") not in (0, 407):
            return {}
        return data.get("data", {}) or {}

    async def set_fill_light(self, sn: str, brightness: int, enabled: bool = True) -> bool:
        """Set the fill light (real endpoint, not /config which only stores in cloud).

        Returns code 309 if device offline or busy.
        """
        data = await self._post(
            "/api/web/device/fill-light-setting",
            {"sn": sn, "lightBrightness": int(brightness), "fillLightSwitch": enabled},
        )
        if data.get("code") == 0:
            _LOGGER.info("Fill light set: brightness=%s enabled=%s", brightness, enabled)
            return True
        _LOGGER.warning("Fill light set failed: %s", data.get("msg"))
        return False

    async def rtk_reboot(self, sn: str) -> bool:
        """Reboot RTK base station."""
        data = await self._post("/api/web/device/rtk-reboot", {"sn": sn})
        return data.get("code") == 0

    async def clean_warnings(self, sn: str) -> bool:
        """Clear warning notifications on the device."""
        data = await self._post("/api/web/device/clean-warn", {"sn": sn})
        return data.get("code") == 0

    async def switch_map(self, sn: str, map_id: str) -> bool:
        """Switch the active map."""
        data = await self._post(
            "/api/web/device/map/switch", {"sn": sn, "map_id": map_id}
        )
        return data.get("code") == 0

    async def _send_command(
        self, endpoint: str, sn: str, extra_data: Dict = None
    ) -> bool:
        """Send a command to the device."""
        payload = {"sn": sn}
        if extra_data:
            payload.update(extra_data)

        data = await self._post(endpoint, payload)
        if data.get("code") == 0:
            _LOGGER.info("Command %s successful for %s", endpoint, sn)
            return True
        _LOGGER.error("Command %s failed: %s (payload was: %s)", endpoint, data.get("msg"), payload)
        return False

    async def start_task(
        self,
        sn: str,
        task_id: str = None,
        map_id: str = None,
        mode: int = 1,
        task_units: list = None,
    ) -> bool:
        """Start mowing task.

        The Airseekers API requires the full task context to start mowing:
        - task_id: ID of the scheduled task
        - map_id: ID of the map to use
        - mode: mowing mode (1 = global)
        - task_units: list of area definitions with cut settings
          (without this, the API returns code -107 "operation not allowed")
        """
        extra = {}
        if task_id:
            extra["task_id"] = task_id
        if map_id:
            extra["map_id"] = map_id
        if mode is not None:
            extra["mode"] = mode
        if task_units:
            extra["task_units"] = task_units
        return await self._send_command(API_TASK_START, sn, extra)

    async def stop_task(self, sn: str) -> bool:
        """Stop mowing task."""
        return await self._send_command(API_TASK_STOP, sn)

    async def pause_task(self, sn: str) -> bool:
        """Pause mowing task."""
        return await self._send_command(API_TASK_PAUSE, sn)

    async def resume_task(self, sn: str) -> bool:
        """Resume mowing task."""
        return await self._send_command(API_TASK_RESUME, sn)

    async def dock(self, sn: str) -> bool:
        """Return to dock."""
        return await self._send_command(API_TASK_DOCK, sn)

    async def lock(self, sn: str, password: str) -> bool:
        """Lock the device."""
        return await self._send_command(API_DEVICE_LOCK, sn, {"password": password})

    async def unlock(self, sn: str, password: str) -> bool:
        """Unlock the device."""
        return await self._send_command(API_DEVICE_UNLOCK, sn, {"password": password})

    def determine_state(
        self,
        device: Dict,
        notifications: List[Dict],
        full_status: Dict = None,
    ) -> str:
        """Determine device state - prefer full_status.task_status, fallback to notifications."""
        if device.get("online_status") != 1:
            return STATE_OFFLINE

        # Primary source: full_status.task_status.state (live from device)
        if full_status:
            task_status = full_status.get("task_status") or {}
            task_state = task_status.get("state")
            # state values observed: 0=idle, 1=mowing/active, 2=paused, others may exist
            if task_state == 1:
                return STATE_MOWING
            if task_state == 2:
                return STATE_PAUSED

            # Check if robot is charging via battery temp / upgrade status or notifications
            battery = full_status.get("battery_status") or {}
            if battery.get("battery_error") and battery.get("battery_error") != 0:
                # still return idle/charging based on context
                pass

        # Fallback: derive state from recent notifications (class 9 only)
        state_notifs = [n for n in (notifications or []) if n.get("notify_class") == 9]
        if not state_notifs:
            return STATE_IDLE

        latest = state_notifs[0]
        notify_type = latest.get("notify_type")

        if notify_type in (900002, 900006, 900061):
            return STATE_MOWING
        if notify_type == 900010:
            return STATE_PAUSED
        if notify_type == 900011:
            return STATE_CHARGING
        if notify_type == 900013:
            return STATE_IDLE
        if notify_type == 900105:
            return STATE_DOCKING
        if notify_type in (900001, 900101, 900036):
            return STATE_IDLE
        if notify_type in (900055, 900018, 900062):
            return STATE_PAUSED
        return STATE_IDLE
