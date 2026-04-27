# Airseekers Tron - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/AdrianTIonut/airseekers-tron-ha.svg)](https://github.com/AdrianTIonut/airseekers-tron-ha/releases)
[![License](https://img.shields.io/github/license/AdrianTIonut/airseekers-tron-ha.svg)](LICENSE)
![GitHub release downloads](https://img.shields.io/github/downloads/AdrianTIonut/airseekers-tron-ha/total)
![Airseekers Tron](https://cdn.hiconsumption.com/wp-content/uploads/2024/04/Tron-360-Vision-Robotic-Lawn-Mower-0-Hero.jpg)

Unofficial Home Assistant custom integration for **Airseekers Tron** robotic lawn mowers.

Communicates with the official Airseekers cloud REST API (discovered through reverse engineering of the Airseekers mobile app).

## What's new in v1.0.7

A new service for advanced control and a smarter `start_mowing` fallback.

### 🛠️ New service: `airseekers_tron.start_mowing_advanced`

Fire a custom mowing job straight from HA, with the same per-zone
control the app gives you:

```yaml
service: airseekers_tron.start_mowing_advanced
data:
  zones: ["A"]            # which polygon zones to mow (skip the rest)
  mode: area              # global / ai / edge / area
  cut_height: 50          # mm
  cut_direction: 90       # degrees (the API stores this in radians)
  cut_speed: fast         # slow / normal / fast
  strategy: dense         # stability / dense / spare  (≈ "Mowing efficiency")
  turning_mode: turn_in_place  # fishtail / circular / turn_in_place
```

Anything you omit is inherited from the first scheduled task you have
in the app, so existing per-zone tuning (cut height, sequence, ...) is
preserved.

### 🔊 Volume + light brightness fixes

- Volume scale fixed from **0-10 → 0-100**. Earlier versions clamped
  to 0-10, which mapped to ~7% volume at the device level (basically
  inaudible). Verified against live cloud state diff: the official app
  sends 0-100 to `/api/web/device/config` under `SetVolume`.
- Light brightness range expanded to **0-100 step 1** (was 10-100 step
  10), matching the granularity the app supports. `0` turns the
  fill-light off.
- `set_light_brightness` now also updates `/api/web/device/config`
  alongside the real-time `fill-light-setting` push, so the cloud
  stays in sync.

### 🔁 Smarter `start_mowing`

`lawn_mower.start_mowing` and `button.airseekers_tron_start_mowing` now
fall back to the most recent executed task when no scheduled task
exists on the account (via `GET /api/web/device/task/latest`). You no
longer need a placeholder schedule in the mobile app — the integration
will replay whatever the user last started by hand.

### 🔎 Reverse-engineered fields (worth knowing)

- `cut_mode` inside `task_units` is the per-zone **"Mowing / No mowing"**
  toggle. `1` = mow this zone, `0` = skip it.
- `path_angle` is in **radians**.
- API field has a typo: `truning_mode` (not `turning_mode`).
- `properties.type` integer on map features: `1` = mowable polygon,
  `3` = boundary, `4`/`5` = no-go zones, `6`/`7` = charge / undock
  points, `8` = RTK base.

---

## What's new in v1.0.6

Gap-analysis pass over the live cloud API surface. Ten new entities fill in
data that the cloud was already returning but we weren't surfacing, plus a
previously-unused firmware endpoint.

New endpoint wired up: `GET /api/web/firmware/latest` → drives a dedicated
`Firmware Upgrade Available` binary sensor and `Firmware Latest` diagnostic
sensor (version, force-upgrade flag, change log as attributes).

New entities from `full_status` data that was already being polled:

| Entity | Source |
|---|---|
| `binary_sensor.*_legacy_task_pending` | `task_status.is_has_legacy_task` — shows when a previous mowing session was interrupted and can be resumed |
| `binary_sensor.*_device_locked` | `lock_status` from the device list (anti-theft state) |
| `binary_sensor.*_voice_pack_upgrade_available` | `/voice-version/latest.upgradable` |
| `sensor.*_explore_state` | `explore_mapping_info.state` + boundary/trajectory pose counts during live mapping |
| `sensor.*_voice_upgrade_progress` / `_state` | `voice_upgrade_status.progress` / `.state` |
| `sensor.*_wifi_ip` | `net_info.wifi_ip` (complements the existing 4G IP sensor) |
| `sensor.*_rtk_lora_channel` | `rtk_info.rtk_channel` + address + numeric quality as attributes |

## Features

### 🤖 Lawn Mower Entity
- Full `lawn_mower` entity with start/pause/dock controls (works with HA's lawn mower card)

### 🎛️ Controls (Buttons)
- ▶️ **Start Mowing** — begins mowing the active map
- ⏸️ **Pause** / **Resume**
- ⏹️ **Stop**
- 🏠 **Return to Dock**
- 🔄 **Reboot RTK** (reboots the RTK base station)
- 🔕 **Clear Warnings** (dismiss device alerts)

### ⚙️ Adjustable Settings
- 🌙 **Night Mode** on/off
- 🔒 **Device Lock** on/off (anti-theft)

### 🔋 Battery & Task Live (from full-status endpoint)
- Battery level (%) and battery temperature (°C)
- Task state, progress %, run time
- Remaining area (m²), current task total area (m²)
- Charging indicator (binary sensor)

### 📍 Position & RTK
- Robot GPS position (latitude, longitude)
- Heading (degrees)
- RTK quality (NARROW_INT, FLOAT, etc.)
- Satellites (count + used)
- LoRa signal strength
- Localization state

### 🌐 Network
- WiFi signal (dBm) and SSID
- 4G IP address and SIM status

### ⚙️ Hardware Versions
- Mower package version (firmware)
- Chassis board, Cutter board, RTK board versions
- Voice pack version and language
- OTA Available indicator (binary sensor)

### 🗺️ Maps & Tasks
- List of saved maps (count + names)
- Number of scheduled tasks
- Active map indicator

### 📊 Statistics
- Total mowed area (m²)
- Total mowing time (hours)
- Total completed tasks

### 🔔 Device Info
- Online status
- NRTK availability (location-based)
- IP address
- Last notification content + type
- Last active timestamp

## Installation

### Via HACS (Custom Repository)

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click the three dots in the top right corner → **Custom repositories**
4. Add repository: `https://github.com/AdrianTIonut/airseekers-tron-ha`
5. Category: **Integration**
6. Click **Add**
7. Search for **"Airseekers Tron"** → Download
8. **Restart Home Assistant**

### Manual Installation

1. Download the latest release from [Releases](https://github.com/AdrianTIonut/airseekers-tron-ha/releases)
2. Copy `custom_components/airseekers_tron` to your HA `custom_components` folder
3. Restart Home Assistant

## Configuration

1. **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Airseekers Tron**
4. Enter your Airseekers account credentials (email and password — same as mobile app)
5. (Optional) Adjust update interval — default is 10 seconds (minimum 5)

## Entities Created

Many entities are **disabled by default** to reduce dashboard clutter. Enable the ones you want from **Settings → Devices → Airseekers Tron → "Entities not shown"**.

<details>
<summary>Full list of entities</summary>

### Lawn Mower
| Entity | Description |
|---|---|
| `lawn_mower.airseekers_tron_XXXXXX` | Main entity with start/pause/dock |

### Buttons
| Entity | Description |
|---|---|
| `button.*_start_mowing` | Start mowing |
| `button.*_stop` | Stop current task |
| `button.*_pause` | Pause |
| `button.*_resume` | Resume |
| `button.*_return_to_dock` | Go to dock |
| `button.*_reboot_rtk` | Reboot RTK (disabled by default) |
| `button.*_clear_warnings` | Clear warnings (disabled by default) |

### Numbers (settings)
| Entity | Range | Working? |
|---|---|---|
| `number.*_volume` | 0-10 | ❌ Does not apply (see Limitations) |
| `number.*_light_brightness` | 0-100 | ❌ Does not apply (see Limitations) |

### Sensors
| Entity | Description |
|---|---|
| `sensor.*_state` | idle, mowing, paused, charging, offline |
| `sensor.*_battery` | Battery percentage |
| `sensor.*_battery_temperature` | °C |
| `sensor.*_task_progress` | % complete |
| `sensor.*_current_task_run_time` | HH:MM:SS |
| `sensor.*_remaining_area` | m² |
| `sensor.*_current_task_total_area` | m² |
| `sensor.*_rtk_quality` | NARROW_INT, FLOAT, etc. |
| `sensor.*_satellites` | Count |
| `sensor.*_position` | `lat, lon` |
| `sensor.*_heading` | degrees (disabled by default) |
| `sensor.*_lora_signal` | dBm (disabled by default) |
| `sensor.*_wifi_signal` | dBm |
| `sensor.*_wifi_ssid` | SSID (disabled by default) |
| `sensor.*_ip_address` | Local IP (disabled by default) |
| `sensor.*_4g_ip` | 4G IP (disabled by default) |
| `sensor.*_firmware` | Package version |
| `sensor.*_chassis_board` | (disabled by default) |
| `sensor.*_cutter_board` | (disabled by default) |
| `sensor.*_rtk_board` | (disabled by default) |
| `sensor.*_last_notification` | Latest notification text |
| `sensor.*_last_active` | Timestamp |
| `sensor.*_night_mode_schedule` | Time range (disabled by default) |
| `sensor.*_maps` | Saved maps count (disabled by default) |
| `sensor.*_scheduled_tasks` | Tasks count (disabled by default) |
| `sensor.*_total_mowed_area` | m² (cumulative) |
| `sensor.*_total_mowing_time` | hours (cumulative) |
| `sensor.*_total_tasks_completed` | (disabled by default) |

### Binary Sensors
| Entity | Description |
|---|---|
| `binary_sensor.*_online` | Robot online |
| `binary_sensor.*_rtk_available` | RTK positioning available |
| `binary_sensor.*_charging` | On dock charging |
| `binary_sensor.*_mcu_upgrade_available` | MCU firmware pending (disabled by default) |
| `binary_sensor.*_firmware_upgrade_available` | Mower firmware pending from cloud (disabled by default) |
| `binary_sensor.*_voice_pack_upgrade_available` | Voice pack update pending (disabled by default) |
| `binary_sensor.*_legacy_task_pending` | Previous mowing session interrupted and resumable |
| `binary_sensor.*_device_locked` | Anti-theft lock state (disabled by default) |

### Switches
| Entity | Description |
|---|---|
| `switch.*_night_mode` | Enable/disable night mode |
| `switch.*_lock_mode` | Anti-theft lock |

### Selects
| Entity | Description |
|---|---|
| `select.*_mowing_mode` | Select mowing mode |

</details>

## Example Automations

### Notify when mowing is complete
```yaml
automation:
  - alias: "Mowing complete notification"
    trigger:
      - platform: state
        entity_id: sensor.airseekers_tron_XXXXXX_state
        from: "mowing"
        to: "idle"
    action:
      - service: notify.mobile_app
        data:
          title: "Lawn Mower"
          message: "Mowing complete! Robot back on dock."
```

### Low battery alert
```yaml
automation:
  - alias: "Tron low battery"
    trigger:
      - platform: numeric_state
        entity_id: sensor.airseekers_tron_XXXXXX_battery
        below: 20
    action:
      - service: notify.mobile_app
        data:
          message: "Tron battery at {{ states('sensor.airseekers_tron_XXXXXX_battery') }}%"
```

### Start mowing at sunrise (if idle and on dock)
```yaml
automation:
  - alias: "Auto mow at sunrise"
    trigger:
      - platform: sun
        event: sunrise
        offset: "+01:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.airseekers_tron_XXXXXX_charging
        state: "on"
      - condition: numeric_state
        entity_id: sensor.airseekers_tron_XXXXXX_battery
        above: 80
    action:
      - service: lawn_mower.start_mowing
        target:
          entity_id: lawn_mower.airseekers_tron_XXXXXX
```

## Lovelace Card Example

```yaml
type: entities
title: Airseekers Tron
entities:
  - entity: lawn_mower.airseekers_tron_XXXXXX
  - entity: sensor.airseekers_tron_XXXXXX_battery
  - entity: sensor.airseekers_tron_XXXXXX_state
  - entity: sensor.airseekers_tron_XXXXXX_task_progress
  - entity: sensor.airseekers_tron_XXXXXX_current_task_run_time
  - entity: sensor.airseekers_tron_XXXXXX_remaining_area
  - entity: sensor.airseekers_tron_XXXXXX_rtk_quality
  - entity: binary_sensor.airseekers_tron_XXXXXX_charging
  - entity: binary_sensor.airseekers_tron_XXXXXX_online
```

## Known Limitations

- **Volume and Light Brightness** cannot be controlled reliably from this integration. Even though the entities exist in HA, the Airseekers cloud REST API returns timeout errors (code 309) when you try to change these values — the setting is accepted by the cloud but never actually applied to the robot. The mobile app works because it uses a direct MQTT connection with protobuf messages (not yet reverse-engineered). The `number.*_volume` and `number.*_light_brightness` entities are kept for future compatibility when MQTT support is added.
- **Camera streaming** is not implemented (would require WebRTC + MQTT)
- **Remote control / joystick** is not implemented (would require real-time MQTT)
- **Per-zone settings** (cutting height, interval, angle) are stored per-map in the Airseekers cloud and not adjustable through the REST API
- **No real-time push** — data is refreshed via polling (default 10s). Real-time MQTT was investigated but is not feasible: the IoT certificate restricts client IDs to a single value used by the robot itself, causing session conflicts.

## Troubleshooting

### Integration not showing up
- Restart Home Assistant completely (not just reload)
- Check HA logs for errors (Settings → System → Logs)
- Make sure HACS download completed

### Authentication failed
- Verify email/password — same as Airseekers mobile app
- If you recently changed password, update in integration settings

### Robot shows offline
- Check robot is powered on and has network (WiFi/4G)
- Open Airseekers app — does it show online?
- Check your WiFi/4G connection in the app

### App disconnects when HA is running
- This is a known limitation: Airseekers cloud only allows one active session per account. HA and mobile app share the same session credentials. Opening the mobile app may temporarily log out HA (and vice-versa). HA reconnects automatically within seconds.

## Contributing

Contributions welcome! If you have an Airseekers Tron and want to help:

1. Fork the repo
2. Create your feature branch
3. Commit your changes
4. Push and open a Pull Request

**Wanted contributions:**
- MQTT protobuf reverse engineering (would enable instant light/volume control during mowing)
- Camera WebRTC stream integration
- Per-zone settings (map geometry API)
- Additional language translations

## Credits

- Integration developed through reverse engineering of the Airseekers mobile app
- Inspired by similar HA integrations for robotic mowers (Husqvarna Automower, Segway Navimow)

## Disclaimer

This is an **unofficial** integration. It is not affiliated with, endorsed by, or connected to Airseekers in any way. Use at your own risk.

## License

MIT License — see [LICENSE](LICENSE) file.

