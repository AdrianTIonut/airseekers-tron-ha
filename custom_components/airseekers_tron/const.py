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
API_WARRANTY = "/api/web/device/warranty/info"
API_EXTENDED_WARRANTY = "/api/web/device/extended-warranty/info"
API_NRTK_SUPPORTED = "/api/web/device/nrtk-supported"
API_VOICE_VERSION = "/api/web/voice-version/latest"
API_TASK_LATEST = "/api/web/device/task/latest"

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
DEFAULT_SCAN_INTERVAL = 10  # seconds - full-status gives real-time data

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


# ---------------------------------------------------------------------------
# Human-readable labels for enum-style integer fields from the API.
# ---------------------------------------------------------------------------

LOCALIZATION_STATE_LABELS = {
    0: "initializing",
    1: "positioning",
    2: "lost",
    3: "relocating",
}

REF_STATION_STATE_LABELS = {
    0: "offline",
    1: "searching",
    2: "connected",
    3: "error",
}

RTK_STATUS_LABELS = {
    "NONE": "no fix",
    "SINGLE": "gps single",
    "FLOAT": "float",
    "WIDE_INT": "rtk wide",
    "NARROW_INT": "rtk fix",
}

TASK_STATE_LABELS = {
    0: "idle",
    1: "running",
    2: "paused",
    3: "finishing",
    4: "error",
}

TASK_TYPE_LABELS = {
    0: "none",
    1: "full mowing",
    2: "area mowing",
    3: "edge mowing",
    4: "explore",
    5: "manual",
}

UPGRADE_STATE_LABELS = {
    0: "idle",
    1: "downloading",
    2: "installing",
    3: "success",
    4: "failed",
}

NET_TYPE_LABELS = {
    0: "offline",
    1: "wifi",
    2: "4g",
    3: "wifi+4g",
}

NRTK_BIND_TYPE_LABELS = {
    0: "none",
    1: "free trial",
    2: "paid",
    3: "permanent",
}

LOCK_STATE_LABELS = {
    0: "unknown",
    1: "locked",
    2: "unlocked",
}

NOTIFY_TYPE_LABELS = {
    900001: "Task completed",
    900002: "Task started",
    900006: "Mowing resumed",
    900010: "Paused",
    900011: "Charging started",
    900013: "Charging complete",
    900018: "Obstacle encountered",
    900036: "Operation aborted",
    900055: "Positioning error",
    900061: "Task resumed",
    900062: "Waiting for signal",
    900101: "Task stopped by user",
    900105: "Returning to dock",
    800004: "RTK base lost signal",
    1100001: "Schedule triggered",
    1200001: "Blade wear warning",
}

# Task-level enums (from observed API payloads)
TASK_MODE_LABELS = {
    0: "global",     # Global Mowing
    1: "ai",         # AI Mowing
    2: "edge",       # Edge Mowing
    3: "area",       # Area Mowing
}
TASK_MODE_LOOKUP = {v: k for k, v in TASK_MODE_LABELS.items()}

# Per-zone (task_unit) enums
CUT_SPEED_LABELS = {
    1: "slow",
    2: "normal",
    3: "fast",
}
CUT_SPEED_LOOKUP = {v: k for k, v in CUT_SPEED_LABELS.items()}

# "Mowing efficiency" in the app — affects how dense the cutting passes are
STRATEGY_LABELS = {
    1: "stability",
    2: "dense",
    3: "spare",
}
STRATEGY_LOOKUP = {v: k for k, v in STRATEGY_LABELS.items()}

# "Turning method" in the app  (note: API spells it "truning_mode" — typo!)
TURNING_MODE_LABELS = {
    1: "fishtail",       # Inner fishtail
    2: "circular",       # Circular turning
    3: "turn_in_place",  # Turn in place
}
TURNING_MODE_LOOKUP = {v: k for k, v in TURNING_MODE_LABELS.items()}

# Map feature `kind` field
MAP_FEATURE_KIND_MOWABLE_POLYGON = 1   # cuttable zone (Polygon with name A/B/...)
MAP_FEATURE_KIND_BORDER = 3            # boundary line of a zone
MAP_FEATURE_KIND_NOGO_A = 4            # no-go zone variant A
MAP_FEATURE_KIND_NOGO_B = 5            # no-go zone variant B
MAP_FEATURE_KIND_CHARGE_POINT = 6      # dock charge point
MAP_FEATURE_KIND_UNDOCK_POINT = 7      # undock point
MAP_FEATURE_KIND_RTK_BASE = 8          # RTK base location

SENSOR_STATUS_BITS = {
    0: "bump_front",
    1: "bump_rear",
    2: "lift",
    3: "tilt",
    4: "rain",
    5: "stall",
    6: "blade_jam",
    7: "blade_missing",
    8: "dock_contact",
    9: "emergency_stop",
    10: "cover_open",
    11: "cliff",
    16: "localization_ok",
    17: "imu_ok",
    18: "wheel_odom_ok",
    19: "camera_ok",
    20: "ultrasonic_ok",
    21: "rtk_ok",
}
