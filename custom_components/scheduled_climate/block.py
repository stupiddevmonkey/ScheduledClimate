"""Schedule block data contract for Scheduled Climate.

A block is one time range of a Home Assistant ``schedule`` helper. The helper
merges the block's custom ``data`` mapping into its own state attributes while
the block is active, so a block is read straight off the schedule entity state.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    ATTR_HUMIDITY,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TEMPERATURE,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import (
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_HUMIDITY,
    DEFAULT_MIN_TEMP,
)
from homeassistant.const import ATTR_SUPPORTED_FEATURES, STATE_ON
from homeassistant.core import State

from .const import (
    ATTR_MAX_HUMIDITY,
    ATTR_MAX_TEMP,
    ATTR_MIN_HUMIDITY,
    ATTR_MIN_TEMP,
)

BLOCK_KEYS = (
    ATTR_HVAC_MODE,
    ATTR_TEMPERATURE,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_FAN_MODE,
    ATTR_HUMIDITY,
)


def _as_number(value: Any) -> float | None:
    """Return a numeric block value, ignoring booleans and other types."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _as_text(value: Any) -> str | None:
    """Return a string block value."""
    return value if isinstance(value, str) and value else None


@dataclass(frozen=True, slots=True)
class ScheduleBlock:
    """The climate settings requested by the active schedule block."""

    hvac_mode: str | None = None
    temperature: float | None = None
    target_temp_low: float | None = None
    target_temp_high: float | None = None
    fan_mode: str | None = None
    humidity: float | None = None

    @classmethod
    def from_state(cls, state: State | None) -> ScheduleBlock | None:
        """Return the active block for a schedule state, or None when inactive."""
        if state is None or state.state != STATE_ON:
            return None

        attributes = state.attributes
        return cls(
            hvac_mode=_as_text(attributes.get(ATTR_HVAC_MODE)),
            temperature=_as_number(attributes.get(ATTR_TEMPERATURE)),
            target_temp_low=_as_number(attributes.get(ATTR_TARGET_TEMP_LOW)),
            target_temp_high=_as_number(attributes.get(ATTR_TARGET_TEMP_HIGH)),
            fan_mode=_as_text(attributes.get(ATTR_FAN_MODE)),
            humidity=_as_number(attributes.get(ATTR_HUMIDITY)),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the configured block values for entity attributes."""
        return {
            ATTR_HVAC_MODE: self.hvac_mode,
            ATTR_TEMPERATURE: self.temperature,
            ATTR_TARGET_TEMP_LOW: self.target_temp_low,
            ATTR_TARGET_TEMP_HIGH: self.target_temp_high,
            ATTR_FAN_MODE: self.fan_mode,
            ATTR_HUMIDITY: self.humidity,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ScheduleBlock:
        """Return a block from a stored mapping, ignoring unusable values."""
        return cls(
            hvac_mode=_as_text(data.get(ATTR_HVAC_MODE)),
            temperature=_as_number(data.get(ATTR_TEMPERATURE)),
            target_temp_low=_as_number(data.get(ATTR_TARGET_TEMP_LOW)),
            target_temp_high=_as_number(data.get(ATTR_TARGET_TEMP_HIGH)),
            fan_mode=_as_text(data.get(ATTR_FAN_MODE)),
            humidity=_as_number(data.get(ATTR_HUMIDITY)),
        )

    @property
    def is_empty(self) -> bool:
        """Return whether the block requests no specific settings."""
        return all(value is None for value in self.as_dict().values())


@dataclass(frozen=True, slots=True)
class ClimateCommand:
    """One climate service call derived from a block."""

    service: str
    data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class BlockPlan:
    """The ordered commands and skipped settings for a block."""

    commands: tuple[ClimateCommand, ...] = ()
    issues: tuple[str, ...] = ()


def _plan_hvac_mode(
    block: ScheduleBlock,
    target: State,
    fallback_modes: Sequence[str],
    issues: list[str],
) -> str | None:
    """Return the HVAC mode to request, or None to leave the mode alone."""
    supported: list[str] = list(target.attributes.get(ATTR_HVAC_MODES) or [])

    if block.hvac_mode is not None:
        if block.hvac_mode not in supported:
            issues.append(f"HVAC mode '{block.hvac_mode}' is not supported")
            return None
        return block.hvac_mode

    if target.state != HVACMode.OFF:
        return None

    candidates = [*fallback_modes, *supported]
    mode = next(
        (
            candidate
            for candidate in candidates
            if candidate != HVACMode.OFF and candidate in supported
        ),
        None,
    )
    if mode is None:
        issues.append("The target has no supported mode to turn on")
    return mode


def _plan_temperature(
    block: ScheduleBlock,
    target: State,
    features: ClimateEntityFeature,
    issues: list[str],
) -> ClimateCommand | None:
    """Return the temperature command for a block, if any."""
    minimum = target.attributes.get(ATTR_MIN_TEMP, DEFAULT_MIN_TEMP)
    maximum = target.attributes.get(ATTR_MAX_TEMP, DEFAULT_MAX_TEMP)

    if block.temperature is not None:
        if not features & ClimateEntityFeature.TARGET_TEMPERATURE:
            issues.append("The target does not support a single target temperature")
        elif not minimum <= block.temperature <= maximum:
            issues.append(
                f"Temperature {block.temperature} is outside {minimum}-{maximum}"
            )
        else:
            return ClimateCommand(
                SERVICE_SET_TEMPERATURE, {ATTR_TEMPERATURE: block.temperature}
            )
        return None

    if block.target_temp_low is None and block.target_temp_high is None:
        return None

    if block.target_temp_low is None or block.target_temp_high is None:
        issues.append("A temperature range needs both a low and a high value")
    elif not features & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE:
        issues.append("The target does not support a target temperature range")
    elif block.target_temp_low >= block.target_temp_high:
        issues.append("The low temperature must be below the high temperature")
    elif not (minimum <= block.target_temp_low and block.target_temp_high <= maximum):
        issues.append(
            f"Temperature range is outside {minimum}-{maximum}",
        )
    else:
        return ClimateCommand(
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_TARGET_TEMP_LOW: block.target_temp_low,
                ATTR_TARGET_TEMP_HIGH: block.target_temp_high,
            },
        )
    return None


def _plan_fan_mode(
    block: ScheduleBlock,
    target: State,
    features: ClimateEntityFeature,
    issues: list[str],
) -> ClimateCommand | None:
    """Return the fan mode command for a block, if any."""
    if block.fan_mode is None:
        return None

    if not features & ClimateEntityFeature.FAN_MODE:
        issues.append("The target does not support fan modes")
        return None

    if block.fan_mode not in (target.attributes.get(ATTR_FAN_MODES) or []):
        issues.append(f"Fan mode '{block.fan_mode}' is not supported")
        return None

    return ClimateCommand(SERVICE_SET_FAN_MODE, {ATTR_FAN_MODE: block.fan_mode})


def _plan_humidity(
    block: ScheduleBlock,
    target: State,
    features: ClimateEntityFeature,
    issues: list[str],
) -> ClimateCommand | None:
    """Return the humidity command for a block, if any."""
    if block.humidity is None:
        return None

    if not features & ClimateEntityFeature.TARGET_HUMIDITY:
        issues.append("The target does not support target humidity")
        return None

    minimum = target.attributes.get(ATTR_MIN_HUMIDITY, DEFAULT_MIN_HUMIDITY)
    maximum = target.attributes.get(ATTR_MAX_HUMIDITY, DEFAULT_MAX_HUMIDITY)
    if not minimum <= block.humidity <= maximum:
        issues.append(f"Humidity {block.humidity} is outside {minimum}-{maximum}")
        return None

    return ClimateCommand(SERVICE_SET_HUMIDITY, {ATTR_HUMIDITY: int(block.humidity)})


def build_plan(
    block: ScheduleBlock,
    target: State,
    fallback_modes: Sequence[str] = (),
) -> BlockPlan:
    """Return the ordered climate commands that apply a block to a target.

    The HVAC mode is always requested first because many devices reject a
    setpoint while they are off.
    """
    issues: list[str] = []
    commands: list[ClimateCommand] = []
    features = ClimateEntityFeature(target.attributes.get(ATTR_SUPPORTED_FEATURES) or 0)

    mode = _plan_hvac_mode(block, target, fallback_modes, issues)
    if mode is not None and mode != target.state:
        commands.append(ClimateCommand(SERVICE_SET_HVAC_MODE, {ATTR_HVAC_MODE: mode}))

    if mode == HVACMode.OFF or (mode is None and target.state == HVACMode.OFF):
        return BlockPlan(tuple(commands), tuple(issues))

    for command in (
        _plan_temperature(block, target, features, issues),
        _plan_fan_mode(block, target, features, issues),
        _plan_humidity(block, target, features, issues),
    ):
        if command is not None:
            commands.append(command)

    return BlockPlan(tuple(commands), tuple(issues))
