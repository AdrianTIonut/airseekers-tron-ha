# Airseekers Tron API Documentation

This document describes the REST API used by the Airseekers Tron integration.

## Base URL

```
https://cloud-eu.airseekers-robotics.com
```

## Authentication

### Login

```http
POST /user/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "...",
    "host": "..."
  },
  "errorCode": 0,
  "msg": "success"
}
```

The `access_token` is a JWT token that expires in approximately 2 hours. Use it in the `Authorization` header for all subsequent requests:

```
Authorization: Bearer <access_token>
```

## Endpoints

### Device Information

#### Get Devices List

```http
GET /api/web/device
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "id": "11911495336153088",
        "sn": "1001014503003803",
        "ip": "192.168.4.98",
        "firmware_ver": "1.3.7",
        "online_status": 1,
        "latest_active_time": 1776700292,
        "timezone_offset": 180,
        "lock_status": 2,
        "iccid": "89464283646104117783",
        "nrtk_bound": true,
        "nrtk_available": true,
        "func_list": ["ai_mowing", "remote_handle", "nrtk"]
      }
    ],
    "total": 1
  }
}
```

#### Get Device Configuration

```http
GET /api/web/device/config?sn={serial_number}
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "configs": {
      "DeviceLock": "0",
      "EnableNRTK": "0",
      "NRTKNetMode": "auto",
      "Net4GAllowUploadPicture": "1",
      "SetDarkMode": "22:00-06:00",
      "SetLightBrightness": "0",
      "SetVolume": "8"
    },
    "is_online_data": true
  }
}
```

#### Set Device Configuration

```http
POST /api/web/device/config
Content-Type: application/json

{
  "sn": "1001014503003803",
  "SetVolume": "5"
}
```

**Available config keys:**
| Key | Values | Description |
|-----|--------|-------------|
| `SetVolume` | "0"-"10" | Robot voice volume |
| `SetLightBrightness` | "0"-"100" | LED brightness |
| `SetDarkMode` | "HH:MM-HH:MM" | Night mode schedule |
| `DeviceLock` | "0"/"1" | Lock status |
| `EnableNRTK` | "0"/"1" | RTK enabled |
| `Net4GAllowUploadPicture` | "0"/"1" | 4G upload enabled |

### Task Control

#### Start Mowing

```http
POST /api/web/device/task/start
Content-Type: application/json

{
  "sn": "1001014503003803"
}
```

#### Stop Mowing

```http
POST /api/web/device/task/stop
Content-Type: application/json

{
  "sn": "1001014503003803"
}
```

#### Pause Mowing

```http
POST /api/web/device/task/pause
Content-Type: application/json

{
  "sn": "1001014503003803"
}
```

#### Resume Mowing

```http
POST /api/web/device/task/resume
Content-Type: application/json

{
  "sn": "1001014503003803"
}
```

#### Return to Dock

```http
POST /api/web/device/task/dock
Content-Type: application/json

{
  "sn": "1001014503003803"
}
```

### Security

#### Lock Device

```http
POST /api/web/device/lock
Content-Type: application/json

{
  "sn": "1001014503003803",
  "password": "1234"
}
```

#### Unlock Device

```http
POST /api/web/device/unlock
Content-Type: application/json

{
  "sn": "1001014503003803",
  "password": "1234"
}
```

### Maps

#### Get Maps

```http
GET /api/web/device/map?sn={serial_number}
```

**Response:**
```json
{
  "code": 0,
  "data": [
    {
      "mapId": "25319660004134912",
      "mapName": "Map-2",
      "nick_name": "hala-fara-margi",
      "geoData": {...}
    }
  ]
}
```

### Scheduled Tasks

#### Get Tasks

```http
GET /api/web/device/task?sn={serial_number}
```

### Task History

#### Get Task Records

```http
GET /api/web/device/task-record/list?sn={serial_number}&page=1&size=10
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "id": "25654622587801600",
        "task_id": "25425404640186368_1776481200",
        "start_time": 1776535495,
        "mow_area": 1379,
        "total_area": 2940,
        "duration": 18956,
        "result": 2,
        "track_file": "https://...",
        "map_url": "https://..."
      }
    ],
    "summary": {
      "total_area": 4969,
      "total_duration": 146150,
      "total_count": 10
    },
    "total": 10
  }
}
```

### Notifications

#### Get Notifications

```http
GET /api/web/device/notify/list?sn={serial_number}&page=1&size=10
```

**Notification Types:**
| Type | Description |
|------|-------------|
| 900001 | Task complete |
| 900002 | Task start |
| 900011 | Charging start |
| 900013 | Charging complete |
| 900055 | Positioning error |

### RTK Information

#### Get RTK Info

```http
GET /api/web/device/rtk/address-info?sn={serial_number}
```

### Firmware

#### Get Latest Firmware

```http
GET /api/web/firmware/latest?sn={serial_number}
```

## Error Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| -107 | Operation not allowed (robot may be busy) |
| 327 | Lock password must be a number |
| 329 | Lock password is incorrect |

## MQTT (Not Implemented)

The following features require MQTT connection which is not available through the REST API:

- Real-time battery level
- Camera streaming
- Remote control (joystick)
- Real-time position updates

The MQTT broker is hosted on AWS IoT:
```
Broker: a26yx9tpysif9b-ats.iot.eu-central-1.amazonaws.com:8883
Protocol: MQTT over TLS with client certificates
```

Certificates can be obtained via `/api/web/device/iot-cert`, but the AWS IoT policy restricts subscription access.
