# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
