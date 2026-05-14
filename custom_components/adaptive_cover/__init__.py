"""The Adaptive Cover integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from .const import (
    CONF_END_ENTITY,
    CONF_ENTITIES,
    CONF_IRRADIANCE_ENTITY,
    CONF_LUX_ENTITY,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_PRESENCE_ENTITY,
    CONF_START_ENTITY,
    CONF_TEMP_ENTITY,
    CONF_WEATHER_ENTITY,
    DOMAIN,
)
from .coordinator import AdaptiveDataUpdateCoordinator

# ── Group service names ────────────────────────────────────────────────────────────────────────────────
_SVC_CLOSE_ALL      = "close_all"
_SVC_OPEN_ALL       = "open_all"
_SVC_ACTIVATE_ALL   = "activate_all"
_SVC_DEACTIVATE_ALL = "deactivate_all"
_GROUP_SERVICES     = [_SVC_CLOSE_ALL, _SVC_OPEN_ALL, _SVC_ACTIVATE_ALL, _SVC_DEACTIVATE_ALL]


def _get_all_coordinators(hass: HomeAssistant) -> list[tuple[str, AdaptiveDataUpdateCoordinator]]:
    """Return (entry_id, coordinator) pairs for every active AC instance."""
    return [
        (entry_id, coord)
        for entry_id, coord in hass.data.get(DOMAIN, {}).items()
        if isinstance(coord, AdaptiveDataUpdateCoordinator)
    ]


def _find_control_switch(hass: HomeAssistant, entry_id: str) -> str | None:
    """Return the entity_id of the Toggle Control switch for a given config entry.

    The unique_id is built as  ``{entry_id}_Toggle Control``  in switch.py.
    """
    registry = er.async_get(hass)
    for entity_entry in registry.entities.values():
        if (
            entity_entry.config_entry_id == entry_id
            and entity_entry.domain == "switch"
            and entity_entry.unique_id == f"{entry_id}_Toggle Control"
        ):
            return entity_entry.entity_id
    return None


def _register_group_services(hass: HomeAssistant) -> None:
    """Register the four group-control services (called once on first entry load)."""

    async def handle_close_all(_call: ServiceCall) -> None:
        """Disable AC on every instance then close all their physical covers."""
        for entry_id, coord in _get_all_coordinators(hass):
            # 1. Disable control via the proper switch path (updates UI state)
            if switch_id := _find_control_switch(hass, entry_id):
                await hass.services.async_call(
                    "switch", "turn_off", {"entity_id": switch_id}, blocking=True
                )
            # 2. Close every physical cover managed by this instance
            for cover_id in coord.entities:
                await hass.services.async_call(
                    "cover", "close_cover", {"entity_id": cover_id}, blocking=False
                )

    async def handle_open_all(_call: ServiceCall) -> None:
        """Disable AC on every instance then open all their physical covers."""
        for entry_id, coord in _get_all_coordinators(hass):
            if switch_id := _find_control_switch(hass, entry_id):
                await hass.services.async_call(
                    "switch", "turn_off", {"entity_id": switch_id}, blocking=True
                )
            for cover_id in coord.entities:
                await hass.services.async_call(
                    "cover", "open_cover", {"entity_id": cover_id}, blocking=False
                )

    async def handle_activate_all(_call: ServiceCall) -> None:
        """Re-enable AC on every instance and reset all manual overrides."""
        for entry_id, coord in _get_all_coordinators(hass):
            # 1. Clear manual overrides so covers return to calculated positions
            for cover_id in list(coord.manager.manual_controlled):
                coord.manager.reset(cover_id)
            # 2. Re-enable control (switch handles coordinator refresh + cover movement)
            if switch_id := _find_control_switch(hass, entry_id):
                await hass.services.async_call(
                    "switch", "turn_on", {"entity_id": switch_id}, blocking=True
                )

    async def handle_deactivate_all(_call: ServiceCall) -> None:
        """Disable AC on every instance without moving any covers."""
        for entry_id, coord in _get_all_coordinators(hass):
            if switch_id := _find_control_switch(hass, entry_id):
                await hass.services.async_call(
                    "switch", "turn_off", {"entity_id": switch_id}, blocking=True
                )

    hass.services.async_register(DOMAIN, _SVC_CLOSE_ALL,      handle_close_all)
    hass.services.async_register(DOMAIN, _SVC_OPEN_ALL,       handle_open_all)
    hass.services.async_register(DOMAIN, _SVC_ACTIVATE_ALL,   handle_activate_all)
    hass.services.async_register(DOMAIN, _SVC_DEACTIVATE_ALL, handle_deactivate_all)

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.BINARY_SENSOR, Platform.BUTTON]
CONF_SUN = ["sun.sun"]


async def async_initialize_integration(
    hass: HomeAssistant,
    config_entry: ConfigEntry | None = None,
) -> bool:
    """Initialize the integration."""

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Cover from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # Register group services once (idempotent guard)
    if not hass.services.has_service(DOMAIN, _SVC_CLOSE_ALL):
        _register_group_services(hass)

    coordinator = AdaptiveDataUpdateCoordinator(hass)
    _temp_entity = entry.options.get(CONF_TEMP_ENTITY)
    _presence_entity = entry.options.get(CONF_PRESENCE_ENTITY)
    _weather_entity = entry.options.get(CONF_WEATHER_ENTITY)
    _cover_entities = entry.options.get(CONF_ENTITIES, [])
    _end_time_entity = entry.options.get(CONF_END_ENTITY)
    _lux_entity = entry.options.get(CONF_LUX_ENTITY)
    _irradiance_entity = entry.options.get(CONF_IRRADIANCE_ENTITY)
    _outside_temp_entity = entry.options.get(CONF_OUTSIDETEMP_ENTITY)
    _start_time_entity = entry.options.get(CONF_START_ENTITY)
    _entities = ["sun.sun"]
    for entity in [
        _temp_entity,
        _presence_entity,
        _weather_entity,
        _end_time_entity,
        _lux_entity,
        _irradiance_entity,
        _outside_temp_entity,
        _start_time_entity,
    ]:
        if entity is not None:
            _entities.append(entity)

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            _entities,
            coordinator.async_check_entity_state_change,
        )
    )

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            _cover_entities,
            coordinator.async_check_cover_state_change,
        )
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    # Remove group services when the last AC instance is gone
    if not hass.data[DOMAIN]:
        for svc in _GROUP_SERVICES:
            hass.services.async_remove(DOMAIN, svc)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
