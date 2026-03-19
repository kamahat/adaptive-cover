"""The Coordinator for Adaptive Cover."""
 
from __future__ import annotations
 
import asyncio
import datetime as dt
from dataclasses import dataclass
 
import numpy as np
import pytz
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.template import state_attr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
 
from .config_context_adapter import ConfigContextAdapter
 
from .calculation import (
    AdaptiveHorizontalCover,
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
    ClimateCoverData,
    ClimateCoverState,
    NormalCoverState,
)
from .const import (
    _LOGGER,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CONF_AWNING_ANGLE,
    CONF_AZIMUTH,
    CONF_BLIND_SPOT_ELEVATION,
    CONF_BLIND_SPOT_LEFT,
    CONF_BLIND_SPOT_RIGHT,
    CONF_CLIMATE_MODE,
    CONF_DEFAULT_HEIGHT,
    CONF_DELTA_POSITION,
    CONF_DELTA_TIME,
    CONF_DISTANCE,
    CONF_ENABLE_BLIND_SPOT,
    CONF_ENABLE_MAX_POSITION,
    CONF_ENABLE_MIN_POSITION,
    CONF_END_ENTITY,
    CONF_END_TIME,
    CONF_ENTITIES,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_HEIGHT_WIN,
    CONF_INTERP,
    CONF_INTERP_END,
    CONF_INTERP_LIST,
    CONF_INTERP_LIST_NEW,
    CONF_INTERP_START,
    CONF_INVERSE_STATE,
    CONF_IRRADIANCE_ENTITY,
    CONF_IRRADIANCE_THRESHOLD,
    CONF_LENGTH_AWNING,
    CONF_LUX_ENTITY,
    CONF_LUX_THRESHOLD,
    CONF_MANUAL_IGNORE_INTERMEDIATE,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_MANUAL_OVERRIDE_RESET,
    CONF_MANUAL_THRESHOLD,
    CONF_MAX_ELEVATION,
    CONF_MAX_POSITION,
    CONF_MIN_ELEVATION,
    CONF_MIN_POSITION,
    CONF_OUTSIDE_THRESHOLD,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_PRESENCE_ENTITY,
    CONF_RETURN_SUNSET,
    CONF_START_ENTITY,
    CONF_START_TIME,
    CONF_SUNRISE_OFFSET,
    CONF_SUNSET_OFFSET,
    CONF_SUNSET_POS,
    CONF_TEMP_ENTITY,
    CONF_TEMP_HIGH,
    CONF_TEMP_LOW,
    CONF_TILT_DEPTH,
    CONF_TILT_DISTANCE,
    CONF_TILT_MODE,
    CONF_TRANSPARENT_BLIND,
    CONF_WEATHER_ENTITY,
    CONF_WEATHER_STATE,
    DOMAIN,
    LOGGER,
)
from .helpers import get_datetime_from_str, get_last_updated, get_safe_state
 
 
@dataclass
class StateChangedData:
    """StateChangedData class."""
 
    entity_id: str
    old_state: State | None
    new_state: State | None
 
 
@dataclass
class AdaptiveCoverData:
    """AdaptiveCoverData class."""
 
    climate_mode_toggle: bool
    states: dict
    attributes: dict
 
 
class AdaptiveDataUpdateCoordinator(DataUpdateCoordinator[AdaptiveCoverData]):
    """Adaptive cover data update coordinator."""
 
    config_entry: ConfigEntry
 
    def __init__(self, hass: HomeAssistant) -> None:  # noqa: D107
        super().__init__(hass, LOGGER, name=DOMAIN)
 
        self.logger = ConfigContextAdapter(_LOGGER)
        self.logger.set_config_name(self.config_entry.data.get("name"))
        self._cover_type = self.config_entry.data.get("sensor_type")
        self._climate_mode = self.config_entry.options.get(CONF_CLIMATE_MODE, False)
        self._switch_mode = True if self._climate_mode else False
        self._inverse_state = self.config_entry.options.get(CONF_INVERSE_STATE, False)
        self._use_interpolation = self.config_entry.options.get(CONF_INTERP, False)
        self._track_end_time = self.config_entry.options.get(CONF_RETURN_SUNSET)
        self._temp_toggle = None
        self._control_toggle = None
        self._manual_toggle = None
 
        # FIX (Bug lux/irradiance au démarrage) :
        # Initialisé à True si l'entité est configurée, plutôt qu'à None.
        # Avec None, `not self._use_lux` est True → lux() retourne False →
        # le mode Winter n'est jamais déclenché lors du premier refresh,
        # avant que les switches aient restauré leur état.
        # True correspond à l'initial_state=True du switch dans switch.py.
        self._lux_toggle = (
            True if self.config_entry.options.get(CONF_LUX_ENTITY) else None
        )
        self._irradiance_toggle = (
            True if self.config_entry.options.get(CONF_IRRADIANCE_ENTITY) else None
        )
 
        self._start_time = None
        self._sun_end_time = None
        self._sun_start_time = None
        # self._end_time = None
        self.manual_reset = self.config_entry.options.get(
            CONF_MANUAL_OVERRIDE_RESET, False
        )
        self.manual_duration = self.config_entry.options.get(
            CONF_MANUAL_OVERRIDE_DURATION, {"minutes": 15}
        )
        self.state_change = False
        self.cover_state_change = False
        self.first_refresh = False
        self.timed_refresh = False
        self.climate_state = None
        self.control_method = "intermediate"
        self.state_change_data: StateChangedData | None = None
        self.manager = AdaptiveCoverManager(self.manual_duration, self.logger)
        self.wait_for_target = {}
        self.target_call = {}
        self.ignore_intermediate_states = self.config_entry.options.get(
            CONF_MANUAL_IGNORE_INTERMEDIATE, False
        )
        self._update_listener = None
        self._scheduled_time = dt.datetime.now()
 
        self._cached_options = None
 
    async def async_config_entry_first_refresh(self) -> None:
        """Config entry first refresh."""
        self.first_refresh = True
        await super().async_config_entry_first_refresh()
        self.logger.debug("Config entry first refresh")
 
    async def async_timed_refresh(self, event) -> None:
        """Control state at end time."""
 
        now = dt.datetime.now()
        if self.end_time is not None:
            time = self.end_time
        if self.end_time_entity is not None:
            time = get_safe_state(self.hass, self.end_time_entity)
 
        self.logger.debug("Checking timed refresh. End time: %s, now: %s", time, now)
 
        time_check = now - get_datetime_from_str(time)
        if time is not None and (time_check <= dt.timedelta(seconds=1)):
            self.timed_refresh = True
            self.logger.debug("Timed refresh triggered")
            await self.async_refresh()
        else:
            self.logger.debug("Timed refresh, but: not equal to end time")
 
    async def async_check_entity_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Fetch and process state change event."""
        self.logger.debug("Entity state change")
        self.state_change = True
        await self.async_refresh()
 
    async def async_check_cover_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Fetch and process state change event."""
        self.logger.debug("Cover state change")
        data = event.data
        if data["old_state"] is None:
            self.logger.debug("Old state is None")
            return
        self.state_change_data = StateChangedData(
            data["entity_id"], data["old_state"], data["new_state"]
        )
        if self.state_change_data.old_state.state != "unknown":
            self.cover_state_change = True
            self.process_entity_state_change()
            await self.async_refresh()
        else:
            self.logger.debug("Old state is unknown, not processing")
 
    def process_entity_state_change(self):
        """Process state change event."""
        event = self.state_change_data
        self.logger.debug("Processing state change event: %s", event)
        entity_id = event.entity_id
        if self.ignore_intermediate_states and event.new_state.state in [
            "opening",
            "closing",
        ]:
            self.logger.debug("Ignoring intermediate state change for %s", entity_id)
            return
        if self.wait_for_target.get(entity_id):
            position = event.new_state.attributes.get(
                "current_position"
                if self._cover_type != "cover_tilt"
                else "current_tilt_position"
            )
            if position == self.target_call.get(entity_id):
                self.wait_for_target[entity_id] = False
                self.logger.debug("Position %s reached for %s", position, entity_id)
            self.logger.debug("Wait for target: %s", self.wait_for_target)
        else:
            self.logger.debug("No wait for target call for %s", entity_id)
 
    @callback
    def _async_cancel_update_listener(self) -> None:
        """Cancel the scheduled update."""
        if self._update_listener:
            self._update_listener()
            self._update_listener = None
 
    async def async_timed_end_time(self) -> None:
        """Control state at end time."""
        self.logger.debug("Scheduling end time update at %s", self._end_time)
        self._async_cancel_update_listener()
        self.logger.debug(
            "End time: %s, Track end time: %s, Scheduled time: %s, Condition: %s",
            self._end_time,
            self._track_end_time,
            self._scheduled_time,
            self._end_time > self._scheduled_time,
        )
        self._update_listener = async_track_point_in_time(
            self.hass, self.async_timed_refresh, self._end_time
        )
        self._scheduled_time = self._end_time
 
    async def _async_update_data(self) -> AdaptiveCoverData:
        self.logger.debug("Updating data")
        if self.first_refresh:
            self._cached_options = self.config_entry.options
 
        options = self.config_entry.options
        self._update_options(options)
 
        # Get data for the blind
        cover_data = self.get_blind_data(options=options)
 
        # Update manager with covers
        self._update_manager_and_covers()
 
        # Access climate data if climate mode is enabled
        if self._climate_mode:
            self.climate_mode_data(options, cover_data)
        else:
            self.logger.debug("Control method is %s", self.control_method)
 
        # calculate the state of the cover
        self.normal_cover_state = NormalCoverState(cover_data)
        self.logger.debug(
            "Determined normal cover state to be %s", self.normal_cover_state
        )
 
        self.default_state = round(self.normal_cover_state.get_state())
        self.logger.debug("Determined default state to be %s", self.default_state)
        state = self.state
 
        await self.manager.reset_if_needed()
 
        if (
            self._end_time
            and self._track_end_time
            and self._end_time > self._scheduled_time
        ):
            await self.async_timed_end_time()
 
        # Handle types of changes
        if self.state_change:
            await self.async_handle_state_change(state, options)
        if self.cover_state_change:
            await self.async_handle_cover_state_change(state)
        if self.first_refresh:
            await self.async_handle_first_refresh(state, options)
        if self.timed_refresh:
            await self.async_handle_timed_refresh(options)
 
        normal_cover
