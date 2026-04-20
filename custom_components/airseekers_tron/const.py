"""Constants for Airseekers Tron integration."""

DOMAIN = "airseekers_tron"

# API URLs
API_BASE_URL = "https://cloud-eu.airseekers-robotics.com"
API_LOGIN = "/user/login"
API_DEVICES = "/api/web/device"
API_TASK = "/api/web/device/task"
API_TASK_START = "/api/web/device/task/start"
API_TASK_STOP = "/api/web/device/task/stop"
API_TASK_PAUSE = "/api/web/device/task/pause"
API_TASK_RESUME = "/api/web/device/task/resume"
API_TASK_DOCK = "/api/web/device/task/dock"
API_DEVICE_MAP = "/api/web/device/map"
API_DEVICE_LOCK = "/api/web/device/lock"
API_DEVICE_UNLOCK = "/api/web/device/unlock"
API_NOTIFY_LIST = "/api/web/device/notify/list"
API_FIRMWARE = "/api/web/firmware/latest"
API_IOT_CERT = "/api/web/device/iot-cert"
API_RTK_INFO = "/api/web/device/rtk/address-info"
API_TASK_RECORD = "/api/web/device/task-record/latest"

# Mowing modes
MOWING_MODE_AI = "ai_mowing"
MOWING_MODE_GLOBAL = "global_mowing"
MOWING_MODE_EDGE = "edge_mowing"
MOWING_MODE_AREA = "area_mowing"
MOWING_MODE_MANUAL = "manual_mode"
MOWING_MODE_REMOTE = "remote_control_mode"

MOWING_MODES = [
    MOWING_MODE_AI,
    MOWING_MODE_GLOBAL,
    MOWING_MODE_EDGE,
    MOWING_MODE_AREA,
    MOWING_MODE_MANUAL,
    MOWING_MODE_REMOTE,
]

# Camera positions
CAMERA_MAIN = "main"
CAMERA_REAR = "rear"
CAMERA_LEFT = "left"
CAMERA_RIGHT = "right"

CAMERAS = [CAMERA_MAIN, CAMERA_REAR, CAMERA_LEFT, CAMERA_RIGHT]

# Config keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_SCAN_INTERVAL = 60  # seconds

# Device states
STATE_IDLE = "idle"
STATE_MOWING = "mowing"
STATE_PAUSED = "paused"
STATE_DOCKING = "docking"
STATE_CHARGING = "charging"
STATE_ERROR = "error"
STATE_OFFLINE = "offline"

# Notification types mapping
NOTIFY_TYPE_CHARGING_COMPLETE = 900013
NOTIFY_TYPE_CHARGING_START = 900011
NOTIFY_TYPE_POSITIONING_ERROR = 900055
NOTIFY_TYPE_TASK_COMPLETE = 900001
NOTIFY_TYPE_TASK_START = 900002

# Attributes
ATTR_SERIAL_NUMBER = "serial_number"
ATTR_FIRMWARE_VERSION = "firmware_version"
ATTR_IP_ADDRESS = "ip_address"
ATTR_ONLINE_STATUS = "online_status"
ATTR_LOCK_STATUS = "lock_status"
ATTR_LAST_NOTIFICATION = "last_notification"
ATTR_NRTK_STATUS = "nrtk_status"
