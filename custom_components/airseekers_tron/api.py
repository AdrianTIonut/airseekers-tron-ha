"""Airseekers Tron API Client."""
import logging
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
        self._token_expiry: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None

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

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid token."""
        if not self._access_token or (
            self._token_expiry and datetime.now() >= self._token_expiry
        ):
            await self.login()

    async def login(self) -> bool:
        """Login to Airseekers API."""
        session = await self._get_session()
        url = f"{API_BASE_URL}{API_LOGIN}"
        payload = {"email": self._email, "password": self._password}

        try:
            async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as resp:
                data = await resp.json()
                
                if data.get("code") != 0:
                    raise AirseekersAuthError(f"Login failed: {data.get('msg', 'Unknown error')}")
                
                self._access_token = data["data"]["access_token"]
                self._refresh_token = data["data"].get("refresh_token")
                self._token_expiry = datetime.now() + timedelta(hours=1, minutes=30)
                
                _LOGGER.debug("Successfully logged in to Airseekers API")
                return True
                
        except aiohttp.ClientError as err:
            raise AirseekersApiError(f"Connection error: {err}") from err

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get list of devices."""
        await self._ensure_authenticated()
        session = await self._get_session()
        url = f"{API_BASE_URL}{API_DEVICES}"

        try:
            async with session.get(url, headers=self._headers()) as resp:
                data = await resp.json()
                if data.get("code") != 0:
                    raise AirseekersApiError(f"Failed to get devices: {data.get('msg')}")
                return data.get("data", {}).get("list", [])
        except aiohttp.ClientError as err:
            raise AirseekersApiError(f"Connection error: {err}") from err

    async def get_device_config(self, sn: str) -> Dict[str, Any]:
        """Get device configuration (volume, light, night mode, etc)."""
        await self._ensure_authenticated()
        session = await self._get_session()
        url = f"{API_BASE_URL}{API_CONFIG}?sn={sn}"

        try:
            async with session.get(url, headers=self._headers()) as resp:
                data = await resp.json()
                if data.get("code") != 0:
                    return {}
                return data.get("data", {}).get("configs", {})
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error getting config: {err}")
            return {}

    async def set_config(self, sn: str, key: str, value: str) -> bool:
        """Set a configuration value."""
        await self._ensure_authenticated()
        session = await self._get_session()
        url = f"{API_BASE_URL}{API_CONFIG}"
        payload = {"sn": sn, key: value}

        try:
            async with session.post(url, json=payload, headers=self._headers()) as resp:
                data = await resp.json()
                if data.get("code") == 0:
                    _LOGGER.info(f"Config {key}={value} set successfully for {sn}")
                    return True
                _LOGGER.error(f"Failed to set config: {data.get('msg')}")
                return False
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error setting config: {err}")
            return False

    async def set_volume(self, sn: str, volume: int) -> bool:
        """Set robot volume (0-10)."""
        return await self.set_config(sn, "SetVolume", str(max(0, min(10, volume))))

    async def set_light_brightness(self, sn: str, brightness: int) -> bool:
        """Set light brightness (0-100)."""
        return await self.set_config(sn, "SetLightBrightness", str(max(0, min(100, brightness))))

    async def set_night_mode(self, sn: str, start_time: str, end_time: str) -> bool:
        """Set night mode schedule (HH:MM-HH:MM)."""
        return await self.set_config(sn, "SetDarkMode", f"{start_time}-{end_time}")

    async def set_4g_upload(self, sn: str, enabled: bool) -> bool:
        """Enable/disable 4G picture upload."""
        return await self.set_config(sn, "Net4GAllowUploadPicture", "1" if enabled else "0")

    async def get_device_tasks(self, sn: str) -> List[Dict[str, Any]]:
        """Get device scheduled tasks."""
        await self._ensure_authenticated()
        session = await self._get_session()
        url = f"{API_BASE_URL}{API_TASK}?sn={sn}"

        try:
            async with session.get(url, headers=self._headers()) as resp:
                data = await resp.json()
                if data.get("code") != 0:
                    return []
                return data.get("data", {}).get("list", [])
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error getting tasks: {err}")
            return []

    async def get_task_history(self, sn: str, page: int = 1, size: int = 10) -> Dict[str, Any]:
        """Get task history with statistics."""
        await self._ensure_authenticated()
        session = await self._get_session()
        url = f"{API_BASE_URL}{API_TASK_RECORD_LIST}?sn={sn}&page={page}&size={size}"

        try:
            async with session.get(url, headers=self._headers()) as resp:
                data = await resp.json()
                if data.get("code") != 0:
                    return {}
                return data.get("data", {})
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error getting task history: {err}")
            return {}

    async def get_notifications(self, sn: str, page: int = 1, size: int = 10) -> List[Dict[str, Any]]:
        """Get device notifications."""
        await self._ensure_authenticated()
        session = await self._get_session()
        url = f"{API_BASE_URL}{API_NOTIFY_LIST}?sn={sn}&page={page}&size={size}"

        try:
            async with session.get(url, headers=self._headers()) as resp:
                data = await resp.json()
                if data.get("code") != 0:
                    return []
                return data.get("data", {}).get("list", [])
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error getting notifications: {err}")
            return []

    async def get_device_map(self, sn: str) -> List[Dict[str, Any]]:
        """Get device maps."""
        await self._ensure_authenticated()
        session = await self._get_session()
        url = f"{API_BASE_URL}{API_DEVICE_MAP}?sn={sn}"

        try:
            async with session.get(url, headers=self._headers()) as resp:
                data = await resp.json()
                if data.get("code") != 0:
                    return []
                return data.get("data", [])
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error getting map: {err}")
            return []

    async def get_rtk_info(self, sn: str) -> Dict[str, Any]:
        """Get RTK information."""
        await self._ensure_authenticated()
        session = await self._get_session()
        url = f"{API_BASE_URL}{API_RTK_INFO}?sn={sn}"

        try:
            async with session.get(url, headers=self._headers()) as resp:
                data = await resp.json()
                return data.get("data", {})
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error getting RTK info: {err}")
            return {}

    async def _send_command(self, endpoint: str, sn: str, extra_data: Dict = None) -> bool:
        """Send a command to the device."""
        await self._ensure_authenticated()
        session = await self._get_session()
        url = f"{API_BASE_URL}{endpoint}"
        payload = {"sn": sn}
        if extra_data:
            payload.update(extra_data)

        try:
            async with session.post(url, json=payload, headers=self._headers()) as resp:
                data = await resp.json()
                if data.get("code") == 0:
                    _LOGGER.info(f"Command {endpoint} successful for {sn}")
                    return True
                _LOGGER.error(f"Command {endpoint} failed: {data.get('msg')}")
                return False
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error sending command: {err}")
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
