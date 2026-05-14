"""Generate values for all types of covers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from math import ceil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import logging

from .cover import AdaptiveGeneralCover, ClimateCoverData, ClimateCoverState
from .sun import SunData


@dataclass
class NormalCoverState:
    """State for normal cover."""

    cover: AdaptiveGeneralCover

    def get_state(self) -> int:
        """Return state of cover."""
        return self.cover.calculate_position()


@dataclass
class ClimateCoverState:
    """State for climate cover."""

    cover: AdaptiveGeneralCover
    climate: ClimateCoverData

    def __post_init__(self):
        """Set climate data."""
        self.climate_data = self.climate
        self.cover_data = self.cover

    def get_state(self) -> int:
        """Return state of cover."""
        return self._get_climate_state()

    def _get_climate_state(self) -> int:
        """Calculate cover position based on climate data."""
        if self.cover.blind_type == "cover_tilt":
            return self.tilt_state()
        return self.normal_type_cover()

    def normal_type_cover(self) -> int:
        """Return position for normal type cover (vertical/horizontal blinds)."""
        if self.climate_data.is_presence:
            return self.normal_with_presence()
        return self.normal_without_presence()

    def normal_without_presence(self) -> int:
        """Return position when no presence detected."""
        if not self.cover.valid:
            return self.cover.default

        if self.climate_data.is_summer:
            return 0
        if self.climate_data.is_winter:
            return 100
        return self.cover.default

    def normal_with_presence(self) -> int:
        """Return position when presence is detected.

        Priority cascade (highest first):
          1. cover.valid gate  — if sun is not in window, return default
          2. Winter check    — open fully to capture solar heat (inside temp used)
          3. Summer check    — close / partial shade
          4. Intermediate    — shade only when direct sun is confirmed
        """
        if not self.cover.valid:
            return self.cover.default

        # ── Step 1 (priority): winter — room needs solar heat ──────────────────────
        # Evaluated BEFORE lux/irradiance so that low illuminance sensors
        # cannot override the heating intent.
        is_summer = self.climate_data.is_summer
        if not is_summer and self.climate_data.is_winter:
            return 100

        # ── Step 2: summer ─────────────────────────────────────────────────────────
        if is_summer:
            if self.cover.transparent_blind:
                return self.cover.calculate_position()
            return 0

        # ── Step 3: intermediate — shade only when direct sun confirmed ────────
        # lux=True  → lux BELOW threshold → not bright enough → no shade
        # irradiance=True → irradiance BELOW threshold → no shade
        # not is_sunny → weather condition not sunny → no shade
        if not is_summer and (
            self.climate_data.lux
            or self.climate_data.irradiance
            or not self.climate_data.is_sunny
        ):
            return self.cover.default

        return self.cover.calculate_position()

    def tilt_state(self) -> int:
        """Return position for tilt type cover (venetian blinds)."""
        if self.climate_data.is_presence:
            return self.tilt_with_presence()
        return self.tilt_without_presence()

    def tilt_without_presence(self) -> int:
        """Return tilt position when no presence."""
        if not self.cover.valid:
            return self.cover.calculate_position()

        if self.climate_data.is_summer:
            return 0
        if self.climate_data.is_winter:
            return self.cover.calculate_tilt_position(mode=2)
        return self.cover.calculate_tilt_position()

    def tilt_with_presence(self) -> int:
        """Return tilt position with presence."""
        if self.cover.valid and (
            self.climate_data.lux
            or self.climate_data.irradiance
            or not self.climate_data.is_sunny
        ):
            return self.cover.calculate_tilt_position()

        if self.climate_data.is_summer:
            return self.cover.calculate_tilt_optimal()
        return self.cover.calculate_position()
