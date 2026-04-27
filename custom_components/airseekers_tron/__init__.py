"""Airseekers Tron integration for Home Assistant."""
import logging
import math
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .api import AirseekersApi
from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    TASK_MODE_LOOKUP,
    CUT_SPEED_LOOKUP,
    STRATEGY_LOOKUP,
    TURNING_MODE_LOOKUP,
    MAP_FEATURE_KIND_MOWABLE_POLYGON,
)
from .coordinator import AirseekersDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.LAWN_MOWER,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SELECT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Airseekers Tron from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    # Create API client
    api = AirseekersApi(email, password)

    try:
        # Login and get devices
        await api.login()
        devices = await api.get_devices()
    except Exception as err:
        _LOGGER.error(f"Failed to connect to Airseekers API: {err}")
        await api.close()
        return False

    if not devices:
        _LOGGER.error("No devices found")
        await api.close()
        return False

    # Create coordinators for each device
    coordinators = {}
    for device in devices:
        sn = device.get("sn")
        coordinator = AirseekersDataCoordinator(hass, api, sn, scan_interval)
        await coordinator.async_config_entry_first_refresh()
        coordinators[sn] = coordinator

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinators": coordinators,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ------------------------------------------------------------------
    # Service: airseekers_tron.start_mowing_advanced
    #
    # Lets the user pick zones (by name "A", "B", ...) and override per-cut
    # settings (height, direction, speed, strategy, turning mode, mode).
    # Anything not specified defaults to the values from the user's first
    # scheduled task in the Airseekers app (the "placeholder" template).
    # ------------------------------------------------------------------
    advanced_schema = vol.Schema({
        vol.Optional("sn"): cv.string,
        vol.Optional("zones"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("mode"): vol.In(list(TASK_MODE_LOOKUP.keys())),
        vol.Optional("cut_height"): vol.All(int, vol.Range(min=20, max=120)),
        vol.Optional("cut_direction"): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=359)
        ),
        # Note: per-zone "Mowing / No mowing" toggle is `cut_mode` in the
        # API — but it's now handled automatically by the `zones` parameter
        # (1 for selected zones, 0 for skipped). No need to expose it here.
        vol.Optional("cut_speed"): vol.In(list(CUT_SPEED_LOOKUP.keys())),
        vol.Optional("strategy"): vol.In(list(STRATEGY_LOOKUP.keys())),
        vol.Optional("turning_mode"): vol.In(list(TURNING_MODE_LOOKUP.keys())),
    })

    async def _start_mowing_advanced(call: ServiceCall) -> None:
        """Build a custom task and start mowing immediately.

        Resolution rules:
        * `zones` (list of names like ["A","B"]) → resolved to areaIds via
          the device's first map. If omitted, all currently configured
          zones in the placeholder schedule are kept.
        * Any setting omitted defaults to whatever is in the placeholder
          schedule's first task_unit (so the user's app-side config wins).
        * `mode` is set at the task level (global/ai/edge/area).
        """
        sn_target = call.data.get("sn")

        for sn, coord in coordinators.items():
            if sn_target and sn != sn_target:
                continue

            # 1. Need a base task to clone (for cutter_sequence + defaults)
            scheduled = coord.data.get("tasks", [])
            if not scheduled:
                _LOGGER.error(
                    "start_mowing_advanced: no scheduled task found in app. "
                    "Create a placeholder schedule with desired zones first."
                )
                continue
            base_task = scheduled[0]
            base_units: list = list(base_task.get("task_units") or [])
            if not base_units:
                _LOGGER.error(
                    "start_mowing_advanced: placeholder schedule has no "
                    "task_units."
                )
                continue
            unit_template = dict(base_units[0])  # defaults for new zones

            # 2. Resolve zone selection
            maps = coord.data.get("maps") or []
            if not maps:
                _LOGGER.error("start_mowing_advanced: no maps loaded.")
                continue
            current_map = maps[0]
            features = (current_map.get("geoData") or {}).get("features") or []
            zone_name_to_id: dict[str, str] = {}
            for feat in features:
                props = feat.get("properties") or {}
                # The map's `properties.type` is an integer that overlaps with
                # the GeoJSON-style geometry.type string elsewhere — keep the
                # integer one. 1 = mowable polygon zone.
                ftype = props.get("type")
                if (
                    ftype == MAP_FEATURE_KIND_MOWABLE_POLYGON
                    and props.get("name")
                ):
                    zone_name_to_id[str(props["name"])] = str(props["id"])
            _LOGGER.debug(
                "start_mowing_advanced: zones available on map: %s",
                list(zone_name_to_id.keys()),
            )

            requested_zones = call.data.get("zones")
            if requested_zones:
                resolved_ids: list[str] = []
                missing: list[str] = []
                for name in requested_zones:
                    aid = zone_name_to_id.get(name)
                    if aid:
                        resolved_ids.append(aid)
                    else:
                        missing.append(name)
                if missing:
                    _LOGGER.error(
                        "start_mowing_advanced: unknown zone(s) %s. "
                        "Available: %s",
                        missing,
                        list(zone_name_to_id.keys()),
                    )
                    continue
                # FIX: Tron's API expects ALL zones to be present in task_units.
                # The "Mowing / No mowing" toggle in the app is the `cut_mode`
                # field per-unit: 1 = mow this zone, 0 = skip it.
                # So we keep every zone the map has, but flip cut_mode based
                # on whether the user requested it.
                new_units: list = []
                seen_ids: set = set()
                # First, copy existing base_units (preserves cutter_sequence
                # and other tuning the user set per zone in the app).
                for u in base_units:
                    nu = dict(u)
                    aid = nu.get("areaId")
                    seen_ids.add(aid)
                    nu["cut_mode"] = 1 if aid in resolved_ids else 0
                    new_units.append(nu)
                # Add any zones from the map that aren't in base_units yet
                # (rare — happens if user added a zone after creating the
                # placeholder schedule).
                for aid in zone_name_to_id.values():
                    if aid not in seen_ids:
                        new_u = dict(unit_template)
                        new_u["areaId"] = aid
                        new_u["cut_mode"] = 1 if aid in resolved_ids else 0
                        new_units.append(new_u)
            else:
                new_units = [dict(u) for u in base_units]

            # 3. Apply per-unit overrides
            cut_height = call.data.get("cut_height")
            cut_direction_deg = call.data.get("cut_direction")
            cut_speed_lbl = call.data.get("cut_speed")
            strategy_lbl = call.data.get("strategy")
            turning_lbl = call.data.get("turning_mode")

            for u in new_units:
                # Don't apply override settings to skipped zones — keep their
                # config as-is, just leave cut_mode=0.
                if u.get("cut_mode") == 0:
                    continue
                if cut_height is not None:
                    u["cutter_height"] = int(cut_height)
                if cut_direction_deg is not None:
                    u["path_angle"] = math.radians(float(cut_direction_deg))
                if cut_speed_lbl is not None:
                    u["cut_speed"] = CUT_SPEED_LOOKUP[cut_speed_lbl]
                if strategy_lbl is not None:
                    u["strategy"] = STRATEGY_LOOKUP[strategy_lbl]
                if turning_lbl is not None:
                    # API typo lives forever
                    u["truning_mode"] = TURNING_MODE_LOOKUP[turning_lbl]

            # 4. Mode at task level
            mode_lbl = call.data.get("mode")
            mode_int = (
                TASK_MODE_LOOKUP[mode_lbl]
                if mode_lbl is not None
                else int(base_task.get("mode") or 0)
            )

            # 5. Send command. If user provided ANY override, treat this as
            # a custom task and OMIT task_id, so the cloud doesn't fall back
            # to the saved task definition (which would re-include all zones
            # and the placeholder's original mode). This mirrors what the
            # app's Quick Mow does (latest_task.task_id is "" when fresh).
            has_overrides = bool(
                requested_zones
                or call.data.get("mode") is not None
                or cut_height is not None
                or cut_direction_deg is not None
                or cut_speed_lbl is not None
                or strategy_lbl is not None
                or turning_lbl is not None
            )
            map_id = current_map.get("mapId") or base_task.get("map_id")
            task_id = (
                None
                if has_overrides
                else (base_task.get("id") or base_task.get("task_id"))
            )
            mowing_count = sum(1 for u in new_units if u.get("cut_mode") == 1)
            _LOGGER.info(
                "start_mowing_advanced: sn=%s task_id=%s map_id=%s mode=%s "
                "total_zones=%d mowing=%d height=%s dir=%s speed=%s "
                "strategy=%s turning=%s overrides=%s",
                sn, task_id or "(none — custom task)", map_id, mode_int,
                len(new_units), mowing_count, cut_height, cut_direction_deg,
                cut_speed_lbl, strategy_lbl, turning_lbl, has_overrides,
            )
            ok = await api.start_task(
                sn,
                task_id=task_id,
                map_id=map_id,
                mode=mode_int,
                task_units=new_units,
            )
            if not ok:
                _LOGGER.error(
                    "start_mowing_advanced: API rejected the command for %s",
                    sn,
                )
            await coord.async_request_refresh()

    if not hass.services.has_service(DOMAIN, "start_mowing_advanced"):
        hass.services.async_register(
            DOMAIN,
            "start_mowing_advanced",
            _start_mowing_advanced,
            schema=advanced_schema,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["api"].close()

    return unload_ok
