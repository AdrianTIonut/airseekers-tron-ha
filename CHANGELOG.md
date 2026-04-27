# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.7] - 2026-04-27

### Added
- **`airseekers_tron.start_mowing_advanced` service** — kick off a custom
  mowing run from HA without touching the app. Optional fields:
  - `zones` (e.g. `["A"]` or `["A","B"]`) — picks which polygon zones to
    mow; the rest get `cut_mode = 0` (skip) so the per-zone "Mowing / No
    mowing" toggle from the app is honoured at the API level.
  - `mode` — `global` / `ai` / `edge` / `area`.
  - `cut_height` (mm), `cut_direction` (degrees, converted to radians),
    `cut_speed`, `strategy` (Mowing efficiency: stability/dense/spare),
    `turning_mode` (Inner fishtail / Circular / Turn in place).
  - Anything not specified inherits from the user's first scheduled task
    in the Airseekers app, so existing per-zone tuning is preserved.
- **`AirseekersApi.get_latest_task(sn)`** wrapping
  `GET /api/web/device/task/latest`. Returns the most recently executed
  task; used as a fallback for `start_mowing` when no scheduled tasks
  exist on the account.
- Per-zone label dictionaries in `const.py`: `TASK_MODE_LABELS`,
  `CUT_SPEED_LABELS`, `STRATEGY_LABELS`, `TURNING_MODE_LABELS`,
  `MAP_FEATURE_KIND_*`. Document the integer enums observed in the live
  API.
- `services.yaml` — description and selectors for the new service so
  Developer Tools → Services renders proper drop-downs.

### Changed
- **`lawn_mower.airseekers_tron.start_mowing` and
  `button.airseekers_tron_start_mowing`** now fall back to the latest
  executed task when there are no scheduled tasks. Previously failed
  silently with `_LOGGER.error("No scheduled tasks found...")`. Users
  no longer need to keep a placeholder schedule in the mobile app.
- **`number.airseekers_tron_volume`** scale fixed from `0-10` to
  `0-100`. Earlier versions clamped the value to 0-10 — that maps
  to "7%" volume on the device, which is barely audible and gave the
  impression that volume control was broken. The cloud's `SetVolume`
  field is on a 0-100 scale (verified by diffing live cloud state
  while dragging the volume slider in the official app).
- **`number.airseekers_tron_light_brightness`** range changed from
  `10-100 step 10` to `0-100 step 1`. The cloud accepts arbitrary
  values in 0..100, and 0 actually turns the fill light off.
- **`set_light_brightness`** now updates `/api/web/device/config`
  alongside the real-time `fill-light-setting` push, mirroring what
  the app does. Keeps the cloud value in sync after a HA-side change.
- **`set_config` body shape fixed**. The cloud previously accepted the
  flat form ``{"sn": ..., "<Key>": "<value>"}`` and replied with
  ``code: 0`` — but silently dropped the write. Verified via
  write→read probe that only the wrapped form saves::

      {"sn": "...", "configs": {"<Key>": "<value>"}}

  This affects **every** entity that goes through ``set_config``:
  Volume, Light Brightness (cloud copy), Device Lock, NRTK, 4G
  picture upload, and Dark Mode (night-mode schedule). They all
  reverted to their previous values after a HA-side change in
  earlier versions.
- **`switch.airseekers_tron_night_mode`** is now actually wired up.
  Turning it ON sends ``SetDarkMode`` with the previously remembered
  schedule (or 22:00-06:00 default); turning it OFF sends an empty
  string, mirroring what the official app does.
- **`night_mode_enabled`** in coordinator state is now derived from
  ``SetDarkMode`` (empty = off, range = on). Earlier versions
  hard-coded it to ``True``.

### Discovered (during reverse engineering)
- `cut_mode` inside `task_units` is a **per-zone mowing toggle**
  (`1` = mow, `0` = skip) — corresponds to the "Mowing / No mowing"
  switch under "Area mowing" in the app. Sending only the zones-to-mow
  in `task_units` is **not** enough; the API requires every configured
  zone to be present, with `cut_mode` flipped accordingly.
- Map `properties.type` (integer) is the feature kind:
  `1` = mowable polygon, `3` = boundary line, `4`/`5` = no-go variants,
  `6` = charge point, `7` = undock point, `8` = RTK base.
- `path_angle` in `task_units` is stored in **radians**, not degrees.
- API field name has a typo: `truning_mode` (not `turning_mode`).
- `start_task` accepts an empty / omitted `task_id` and treats the
  request as a fresh custom task — required when overriding zones or
  cut settings, otherwise the server falls back to the saved task
  definition and ignores overrides.

---

## [1.0.6] - 2026-04-23

### Added
- `GET /api/web/firmware/latest` is now polled; surfaces as
  `binary_sensor.*_firmware_upgrade_available` and
  `sensor.*_firmware_latest` (with `current_version`, `force_upgrade`,
  `change_log` as attributes).
- `binary_sensor.*_voice_pack_upgrade_available` — complements the
  existing `sensor.*_voice_pack_latest` with a device-class update sensor.
- `binary_sensor.*_legacy_task_pending` — surfaces
  `task_status.is_has_legacy_task`; fires when a previous mowing session
  was interrupted and can be resumed from the app.
- `binary_sensor.*_device_locked` — anti-theft lock state from
  `lock_status` (separate from the `DeviceLock` config switch).
- `sensor.*_explore_state` — mapping-session state, with boundary and
  trajectory pose counts as attributes.
- `sensor.*_voice_upgrade_progress` / `sensor.*_voice_upgrade_state` —
  parity with the MCU upgrade sensors that already existed.
- `sensor.*_wifi_ip` — WiFi-side IP address (was previously missing;
  only the 4G IP was exposed).
- `sensor.*_rtk_lora_channel` — currently-negotiated LoRa channel on the
  RTK radio, with address and numeric quality as attributes.
- `AirseekersApi.get_firmware_latest(sn)` helper; accepts both code 0
  and code 407 (already-latest) as success.

### Changed
- Renamed `binary_sensor.*_ota_available` label to "MCU Upgrade
  Available" (unique_id unchanged) to distinguish it from the new
  mower-firmware upgrade sensor.
- Coordinator fetches warranty, extended warranty, NRTK availability,
  voice version, last task record, and latest firmware in a single
  `asyncio.gather`.

### Fixed
- Restored `api.py` and `coordinator.py` after a truncation mishap
  during the v1.0.5 → v1.0.6 refactor.

## [1.0.5] - 2026-04-20

### Added
- **Real-time device state** via `/api/web/device/full-status` endpoint.
  The state detection now uses the actual `task_status.state` reported
  by the robot instead of parsing notifications.
- **Battery sensor** (percentage) with proper `battery` device_class.
- **Battery Temperature sensor** (°C).
- **Task progress sensor** (calculated % based on remaining vs total area).
- **Current task sensors**: Run Time, Remaining Area, Current Total Area.
- **Position sensors**: Latitude/Longitude (as `lat, lon` string with
  separate attributes), Heading (degrees).
- **RTK sensors**: RTK Quality (NARROW_INT, etc), Satellites (count +
  used), LoRa Signal (dBm, disabled by default).
- **Network sensors**: WiFi Signal (dBm), WiFi SSID, 4G IP (most
  disabled by default to reduce noise).
- **Version sensors** for each board: Chassis Board, Cutter Board,
  RTK Board (disabled by default).
- **Binary sensors**: Charging (true when robot is docked), OTA
  Available (true when MCU upgrade is pending).
- **RTK Reboot button** (disabled by default).
- **Clear Warnings button** (disabled by default).

### Fixed
- **Light brightness command** now uses correct endpoint
  `/api/web/device/fill-light-setting` with `lightBrightness` field.
  The old `/config` endpoint was read-only despite returning `code 0`.
- **Default scan interval** lowered to 10s (was 60s); minimum lowered to
  5s since `full-status` returns fresh data on every call.

### Notes
- MQTT direct connection was researched but not implemented: the
  `iot-cert` endpoint returns a cert whose IAM policy restricts the
  client_id to a single value used by the robot itself, causing
  session takeover conflicts when a separate client connects.

## [1.0.4] - 2026-04-20

### Fixed
- State detection now correctly reflects the robot's activity. Previous
  version only handled 4 notify types; now handles all relevant ones:
  `900006`, `900061` (mowing), `900010` (paused), `900011` (charging),
  `900013` (idle after charge), `900101` (terminated), `900036` (task
  failed), `900105` (returning to dock), `900055`, `900018`, `900062`
  (auto-paused for positioning/lift/escape errors).
- State detection now filters out communication errors (`notify_class: 8`
  like "RTK signal lost") which don't reflect work state.

## [1.0.3] - 2026-04-20

### Fixed
- **Critical**: Start Mowing now actually starts the robot. API returns
  `code -107` (operation not allowed) unless the payload includes the
  full `task_units` array (with cut_mode, cut_speed, cutter_height,
  path_angle, strategy, turning_mode, zigzag_dis for each area).
- Integration now reads `task_units` from the scheduled task and
  forwards them with the start command.

## [1.0.2] - 2026-04-20

### Fixed
- **Critical**: Start Mowing button now works! The previous payload was
  incomplete - the API requires `task_id`, `map_id`, and `mode` parameters
  in addition to `sn`. Without these, the cloud accepted the request
  (returning code 0) but never forwarded it to the robot.
- `start_task()` now pulls task/map context from the scheduled tasks
  list (populated by the coordinator) and includes them in the POST.
- Improved error logging: failed commands now include the full payload
  for easier debugging.

### Requirements
- A scheduled task must exist on the robot (created in the mobile app).
  Without it, the Start button logs an error instead of silently doing
  nothing.

## [1.0.1] - 2026-04-20

### Fixed
- **Critical**: Added `asyncio.Lock()` to prevent concurrent re-login attempts
  that would invalidate each other's tokens (race condition when multiple
  parallel requests all get auth errors simultaneously).
- Re-login logic now covers **all** API methods (previously only `get_devices`
  and `_send_command` had it; now every GET and POST goes through `_get`/`_post`
  helpers with automatic retry on auth failure).
- Auth error detection now includes HTTP 401 status (in addition to response
  body messages like "illegal credentials", "invalid token", etc.).
- Fixed URL parameter handling: use `params={}` instead of f-string
  concatenation (prevents double-encoding and edge cases).
- Removed arbitrary 1.5h token expiry timer — re-login is now driven only by
  actual API responses, which is the real signal.

### Changed
- Refactored `api.py`: centralized GET/POST logic in `_get()` and `_post()`
  helpers, eliminating code duplication across ~10 endpoints.

## [1.0.0] - 2026-04-20

### Added
- Initial release
- Lawn mower entity with start/pause/dock controls
- Button entities for Start, Stop, Pause, Resume, Return to Dock
- Number entities for Volume (0-10) and Light Brightness (0-100%)
- Sensor entities:
  - State (idle, mowing, charging, offline)
  - Last Notification
  - Scheduled Tasks count
  - Maps count
  - Firmware version
  - Last Active timestamp
  - Total Mowed Area (m²)
  - Total Mowing Time (hours)
  - Total Tasks Completed
  - IP Address
  - Night Mode Schedule
- Binary sensor entities for Online status and RTK availability
- Switch entities for Night Mode and Lock Mode
- Select entity for Mowing Mode
- Config flow for easy setup through UI
- HACS compatibility

### Known Limitations
- Battery level not available (requires MQTT)
- Camera streaming not supported (requires WebRTC/MQTT)
- Remote control not available (requires real-time MQTT)
- Area-specific settings stored per-map, not adjustable via API
