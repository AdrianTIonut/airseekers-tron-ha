# Airseekers Tron - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/AdrianTIonut/airseekers-tron-ha.svg)](https://github.com/AdrianTIonut/airseekers-tron-ha/releases)
[![License](https://img.shields.io/github/license/AdrianTIonut/airseekers-tron-ha.svg)](LICENSE)

Home Assistant custom integration for **Airseekers Tron** robotic lawn mowers.

![Airseekers Tron](https://www.airseekers.com/cdn/shop/files/TRON-1.png?v=1701234567&width=400)

## Features

### Controls
- ▶️ **Start** mowing
- ⏸️ **Pause** mowing  
- ⏹️ **Stop** mowing
- 🔄 **Resume** mowing
- 🏠 **Return to dock**
- 🔒 **Lock/Unlock** robot

### Settings (adjustable from HA)
- 🔊 **Volume** (0-10)
- 💡 **Light Brightness** (0-100%)
- 🌙 **Night Mode** schedule

### Sensors
- 📊 **State** (idle, mowing, charging, offline)
- 🌐 **Online Status**
- 📍 **IP Address**
- 📡 **RTK Status**
- 🗺️ **Maps Count**
- 📅 **Scheduled Tasks**
- 🔔 **Last Notification**
- ⚙️ **Firmware Version**
- ⏱️ **Last Active Time**

### Statistics
- 🌿 **Total Mowed Area** (m²)
- ⏰ **Total Mowing Time** (hours)
- 📈 **Total Tasks Completed**

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/AdrianTIonut/airseekers-tron-ha`
6. Select category: "Integration"
7. Click "Add"
8. Search for "Airseekers Tron" and install it
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/AdrianTIonut/airseekers-tron-ha/releases)
2. Extract and copy the `custom_components/airseekers_tron` folder to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Airseekers Tron**
4. Enter your Airseekers account credentials (email and password)
5. Set the update interval (default: 60 seconds)

## Entities Created

| Entity Type | Name | Description |
|-------------|------|-------------|
| `lawn_mower` | Airseekers Tron | Main entity with start/pause/dock controls |
| `button` | Start Mowing | Start a mowing task |
| `button` | Stop | Stop current task |
| `button` | Pause | Pause current task |
| `button` | Resume | Resume paused task |
| `button` | Return to Dock | Send robot to charging station |
| `number` | Volume | Robot voice volume (0-10) |
| `number` | Light Brightness | LED brightness (0-100%) |
| `sensor` | State | Current robot state |
| `sensor` | Last Notification | Latest notification message |
| `sensor` | Scheduled Tasks | Number of scheduled tasks |
| `sensor` | Maps | Number of saved maps |
| `sensor` | Firmware | Current firmware version |
| `sensor` | Last Active | Last activity timestamp |
| `sensor` | Total Mowed Area | Cumulative mowed area |
| `sensor` | Total Mowing Time | Cumulative mowing time |
| `sensor` | Total Tasks Completed | Total completed tasks |
| `sensor` | IP Address | Robot's local IP address |
| `sensor` | Night Mode Schedule | Night mode time range |
| `binary_sensor` | Online | Robot online status |
| `binary_sensor` | RTK Available | RTK positioning available |
| `switch` | Night Mode | Enable/disable night mode |
| `switch` | Lock Mode | Enable/disable anti-theft lock |
| `select` | Mowing Mode | Select mowing mode |

## Example Automations

### Start mowing at sunrise
```yaml
automation:
  - alias: "Start mowing at sunrise"
    trigger:
      - platform: sun
        event: sunrise
        offset: "+01:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.airseekers_tron_XXXXXX_online
        state: "on"
    action:
      - service: lawn_mower.start_mowing
        target:
          entity_id: lawn_mower.airseekers_tron_XXXXXX
```

### Send notification when mowing complete
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
          message: "Mowing complete! Robot is back at the dock."
```

### Reduce volume at night
```yaml
automation:
  - alias: "Reduce mower volume at night"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.airseekers_tron_XXXXXX_volume
        data:
          value: 2
```

## Lovelace Card Example

```yaml
type: entities
title: Airseekers Tron
entities:
  - entity: lawn_mower.airseekers_tron_XXXXXX
  - entity: sensor.airseekers_tron_XXXXXX_state
  - entity: binary_sensor.airseekers_tron_XXXXXX_online
  - entity: number.airseekers_tron_XXXXXX_volume
  - entity: number.airseekers_tron_XXXXXX_light_brightness
  - entity: sensor.airseekers_tron_XXXXXX_total_mowed_area
  - entity: sensor.airseekers_tron_XXXXXX_total_mowing_time
```

## API Documentation

This integration uses the Airseekers Cloud REST API. For detailed API documentation, see [API.md](API.md).

## Known Limitations

- **Battery level** is not available through the REST API (requires MQTT connection)
- **Camera streaming** is not supported (requires WebRTC/MQTT)
- **Remote control** (joystick) is not available (requires real-time MQTT)
- **Area-specific settings** (height, interval, angle) are stored per-map and not adjustable via API

## Troubleshooting

### Integration not showing up
- Make sure you've restarted Home Assistant after installation
- Check the Home Assistant logs for errors

### Authentication failed
- Verify your email and password are correct
- Make sure you can log in to the Airseekers mobile app

### Robot shows as offline
- Check that your robot is powered on and connected to the internet
- Verify the robot appears online in the Airseekers mobile app

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Credits

- Developed through reverse engineering of the Airseekers mobile app
- Thanks to the Home Assistant community

## Disclaimer

This is an unofficial integration and is not affiliated with, endorsed by, or connected to Airseekers in any way. Use at your own risk.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
