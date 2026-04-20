# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
