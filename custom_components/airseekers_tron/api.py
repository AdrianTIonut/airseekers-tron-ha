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
    STATE_IDLE,
    STATE_MOWING,
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
        """Set a configuration value."""
        data = await self._post(API_CONFIG, {"sn": sn, key: value})
        if data.get("code") == 0:
            _LOGGER.info("Config %s=%s set successfully for %s", key, value, sn)
            return True
        _LOGGER.error("Failed to set config: %s", data.get("msg"))
        return False

    async def set_volume(self, sn: str, volume: int) -> bool:
        """Set robot volume (0-10)."""
        return await self.set_config(sn, "SetVolume", str(max(0, min(10, volume))))

    async def set_light_brightness(self, sn: str, brightness: int) -> bool:
        """Set light brightness (0-100)."""
        return await self.set_config(
            sn, "SetLightBrightness", str(max(0, min(100, brightness)))
        )

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
        _LOGGER.error("Command %s failed: %s", endpoint, data.get("msg"))
        return False

    async def start_task(self, sn: str) -> bool:
        """Start mowing task."""
        return await self._send_command(API_TASK_START, sn)

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

    def determine_state(self, device: Dict, notifications: List[Dict]) -> str:
        """Determine device state from device info and notifications."""
        if device.get("online_status") != 1:
            return STATE_OFFLINE

        if notifications:
            latest = notifications[0]
            notify_type = latest.get("notify_type")
            if notify_type == 900013:  # Charging complete
                return STATE_IDLE
            elif notify_type == 900011:  # Charging start
                return STATE_CHARGING
            elif notify_type == 900001:  # Task complete
                return STATE_IDLE
            elif notify_type == 900002:  # Task start
                return STATE_MOWING

        return STATE_IDLE
