"""Config flow for Adaptive Cover integration."""
 
from __future__ import annotations
 
from typing import Any
 
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
 
from .const import (
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
    CONF_MODE,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_PRESENCE_ENTITY,
    CONF_RETURN_SUNSET,
    CONF_SENSOR_TYPE,
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
    CONF_OUTSIDE_THRESHOLD,
    DOMAIN,
    SensorType,
    CONF_MIN_POSITION,
    CONF_ENABLE_MAX_POSITION,
    CONF_ENABLE_MIN_POSITION,
)
 
# DEFAULT_NAME = "Adaptive Cover"
 
SENSOR_TYPE_MENU = [SensorType.BLIND, SensorType.AWNING, SensorType.TILT]
 
 
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("name"): selector.TextSelector(),
        vol.Optional(CONF_MODE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=SENSOR_TYPE_MENU, translation_key="mode"
            )
        ),
    }
)
 
CLIMATE_MODE = vol.Schema(
    {
        vol.Optional(CONF_CLIMATE_MODE, default=False): selector.BooleanSelector(),
    }
)
 
OPTIONS = vol.Schema(
    {
        vol.Required(CONF_AZIMUTH, default=180): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=359, mode="slider", unit_of_measurement="°"
            )
        ),
        vol.Required(CONF_DEFAULT_HEIGHT, default=60): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=100, step=1, mode="slider", unit_of_measurement="%"
            )
        ),
        vol.Optional(CONF_MAX_POSITION): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=100)
        ),
        vol.Optional(CONF_ENABLE_MAX_POSITION, default=False): bool,
        vol.Optional(CONF_MIN_POSITION): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=99)
        ),
        vol.Optional(CONF_ENABLE_MIN_POSITION, default=False): bool,
        vol.Optional(CONF_MIN_ELEVATION): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=90)
        ),
        vol.Optional(CONF_MAX_ELEVATION): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=90)
        ),
        vol.Required(CONF_FOV_LEFT, default=90): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=90, step=1, mode="slider", unit_of_measurement="°"
            )
        ),
        vol.Required(CONF_FOV_RIGHT, default=90): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=90, step=1, mode="slider", unit_of_measurement="°"
            )
        ),
        vol.Required(CONF_SUNSET_POS, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=100, step=1, mode="slider", unit_of_measurement="%"
            )
        ),
        vol.Required(CONF_SUNSET_OFFSET, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(mode="box", unit_of_measurement="minutes")
        ),
        vol.Required(CONF_SUNRISE_OFFSET, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(mode="box", unit_of_measurement="minutes")
        ),
        vol.Required(CONF_INVERSE_STATE, default=False): bool,
        vol.Required(CONF_ENABLE_BLIND_SPOT, default=False): bool,
        vol.Required(CONF_INTERP, default=False): bool,
    }
)
 
VERTICAL_OPTIONS = vol.Schema(
    {
        vol.Optional(CONF_ENTITIES, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(
                multiple=True,
                filter=selector.EntityFilterSelectorConfig(
                    domain="cover",
                    supported_features=["cover.CoverEntityFeature.SET_POSITION"],
                ),
            )
        ),
        vol.Required(CONF_HEIGHT_WIN, default=2.1): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1, max=6, step=0.01, mode="slider", unit_of_measurement="m"
            )
        ),
        vol.Required(CONF_DISTANCE, default=0.5): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1, max=2, step=0.1, mode="slider", unit_of_measurement="m"
            )
        ),
    }
).extend(OPTIONS.schema)
 
 
HORIZONTAL_OPTIONS = vol.Schema(
    {
        vol.Required(CONF_LENGTH_AWNING, default=2.1): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.3, max=6, step=0.01, mode="slider", unit_of_measurement="m"
            )
        ),
        vol.Required(CONF_AWNING_ANGLE, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=45, mode="slider", unit_of_measurement="°"
            )
        ),
    }
).extend(VERTICAL_OPTIONS.schema)
 
TILT_OPTIONS = vol.Schema(
    {
        vol.Optional(CONF_ENTITIES, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(
                multiple=True,
                filter=selector.EntityFilterSelectorConfig(
                    domain="cover",
                    supported_features=["cover.CoverEntityFeature.SET_TILT_POSITION"],
                ),
            )
        ),
        vol.Required(CONF_TILT_DEPTH, default=3): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1, max=15, step=0.1, mode="slider", unit_of_measurement="cm"
            )
        ),
        vol.Required(CONF_TILT_DISTANCE, default=2): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1, max=15, step=0.1, mode="slider", unit_of_measurement="cm"
            )
        ),
        vol.Required(CONF_TILT_MODE, default="mode2"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["mode1", "mode2"], translation_key="tilt_mode"
            )
        ),
    }
).extend(OPTIONS.schema)
 
CLIMATE_OPTIONS = vol.Schema(
    {
        vol.Required(CONF_TEMP_ENTITY): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(domain=["climate", "sensor"])
        ),
        vol.Required(CONF_TEMP_LOW, default=21): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=86, step=1, mode="slider", unit_of_measurement="°"
            )
        ),
        vol.Required(CONF_TEMP_HIGH, default=25): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=90, step=1, mode="slider", unit_of_measurement="°"
            )
        ),
        vol.Optional(
            CONF_OUTSIDETEMP_ENTITY, default=vol.UNDEFINED
        ): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(domain=["sensor"])
        ),
        vol.Optional(CONF_OUTSIDE_THRESHOLD, default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
        vol.Optional(
            CONF_PRESENCE_ENTITY, default=vol.UNDEFINED
        ): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(
                domain=["device_tracker", "zone", "binary_sensor", "input_boolean"]
            )
        ),
        vol.Optional(CONF_LUX_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(
                domain=["sensor"], device_class="illuminance"
            )
        ),
        vol.Optional(CONF_LUX_THRESHOLD, default=1000): selector.NumberSelector(
            selector.NumberSelectorConfig(mode="box", unit_of_measurement="lux")
        ),
        vol.Optional(
            CONF_IRRADIANCE_ENTITY, default=vol.UNDEFINED
        ): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(
                domain=["sensor"], device_class="irradiance"
            )
        ),
        vol.Optional(CONF_IRRADIANCE_THRESHOLD, default=300): selector.NumberSelector(
            selector.NumberSelectorConfig(mode="box", unit_of_measurement="W/m²")
        ),
        vol.Optional(CONF_TRANSPARENT_BLIND, default=False): selector.BooleanSelector(),
        vol.Optional(
            CONF_WEATHER_ENTITY, default=vol.UNDEFINED
        ): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(domain="weather")
        ),
    }
)
 
WEATHER_OPTIONS = vol.Schema(
    {
        vol.Optional(
            CONF_WEATHER_STATE, default=["sunny", "partlycloudy", "cloudy", "clear"]
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                multiple=True,
                sort=False,
                options=[
                    "clear-night",
                    "clear",
                    "cloudy",
                    "fog",
                    "hail",
                    "lightning",
                    "lightning-rainy",
                    "partlycloudy",
                    "pouring",
                    "rainy",
                    "snowy",
                    "snowy-rainy",
                    "sunny",
                    "windy",
                    "windy-variant",
                    "exceptional",
                ],
            )
        )
    }
)
 
 
AUTOMATION_CONFIG = vol.Schema(
    {
        vol.Required(CONF_DELTA_POSITION, default=1): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=90, step=1, mode="slider", unit_of_measurement="%"
            )
        ),
        vol.Optional(CONF_DELTA_TIME, default=2): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=2, mode="box", unit_of_measurement="minutes"
            )
        ),
        vol.Optional(CONF_START_TIME, default="00:00:00"): selector.TimeSelector(),
        vol.Optional(CONF_START_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_datetime"])
        ),
        vol.Required(
            CONF_MANUAL_OVERRIDE_DURATION, default={"minutes": 15}
        ): selector.DurationSelector(),
        vol.Required(CONF_MANUAL_OVERRIDE_RESET, default=False)
