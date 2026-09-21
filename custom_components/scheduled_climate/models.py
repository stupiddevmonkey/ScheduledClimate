"""Typed configuration models for Scheduled Climate.

A config entry describes one *room*: a set of climate targets, a set of named
schedule *plans*, and the rule that decides which plan is active. Entry data and
options stay plain JSON; these dataclasses are the only place that knows how to
read and write that shape.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Self

from homeassistant.config_entries import ConfigEntry
from homeassistant.util.ulid import ulid_now

from .const import (
    CONF_APPLY_ON_START,
    CONF_DEFAULT_HVAC_MODE,
    CONF_HYSTERESIS,
    CONF_LEGACY_OFF_TIME,
    CONF_LEGACY_ON_TIME,
    CONF_OFF_BEHAVIOR,
    CONF_OUTDOOR_TEMP_ENTITY_ID,
    CONF_OVERRIDE,
    CONF_OVERRIDE_DEFAULT_MINUTES,
    CONF_OVERRIDE_MAX_MINUTES,
    CONF_PLAN_ICON,
    CONF_PLAN_ID,
    CONF_PLAN_MIN_OUTDOOR_TEMP,
    CONF_PLAN_NAME,
    CONF_PLAN_SCHEDULES,
    CONF_PLAN_SELECTION,
    CONF_PLAN_SELECTION_MODE,
    CONF_PLANS,
    CONF_SCHEDULE_ENABLED,
    CONF_SUSTAIN_MINUTES,
    CONF_TARGET_ENTITY_ID,
    CONF_TARGET_KEY,
    CONF_TARGET_NAME,
    CONF_TARGETS,
    DEFAULT_APPLY_ON_START,
    DEFAULT_HVAC_MODE,
    DEFAULT_HYSTERESIS,
    DEFAULT_OFF_BEHAVIOR,
    DEFAULT_OVERRIDE_MAX_MINUTES,
    DEFAULT_OVERRIDE_MINUTES,
    DEFAULT_PLAN_SELECTION_MODE,
    DEFAULT_SCHEDULE_ENABLED,
    DEFAULT_SUSTAIN_MINUTES,
    OFF_BEHAVIORS,
    PLAN_MODE_MANUAL,
    PLAN_MODE_OUTDOOR_TEMP,
    PLAN_MODES,
)

EMPTY_MAPPING: Mapping[str, Any] = MappingProxyType({})


def new_key() -> str:
    """Return a fresh identifier for a target or a plan."""
    return ulid_now()


def _as_float(value: Any) -> float | None:
    """Return a finite float, or None when the value is not numeric."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _as_positive_int(value: Any, default: int) -> int:
    """Return a positive integer, falling back to the default."""
    number = _as_float(value)
    if number is None or number < 1:
        return default
    return int(number)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """Return a mapping, or an empty one when the stored value is corrupt.

    Options survive hand editing and failed migrations, so every parser here
    degrades to defaults rather than raising. A config entry that cannot be
    parsed would also break the options flow used to repair it.
    """
    return value if isinstance(value, Mapping) else EMPTY_MAPPING


def _as_items(value: Any) -> Sequence[Any]:
    """Return a list of stored items, ignoring anything that is not a list."""
    return value if isinstance(value, (list, tuple)) else ()


@dataclass(frozen=True, slots=True)
class TargetConfig:
    """One climate entity controlled by the room."""

    key: str
    entity_id: str
    name: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self | None:
        """Return a target from stored data, or None when it is unusable."""
        entity_id = data.get(CONF_TARGET_ENTITY_ID)
        key = data.get(CONF_TARGET_KEY)
        if not isinstance(entity_id, str) or not entity_id:
            return None
        if not isinstance(key, str) or not key:
            return None
        name = data.get(CONF_TARGET_NAME)
        return cls(
            key=key,
            entity_id=entity_id,
            name=name if isinstance(name, str) and name else entity_id,
        )

    def as_dict(self) -> dict[str, str]:
        """Return the stored representation."""
        return {
            CONF_TARGET_KEY: self.key,
            CONF_TARGET_ENTITY_ID: self.entity_id,
            CONF_TARGET_NAME: self.name,
        }


@dataclass(frozen=True, slots=True)
class TargetBehavior:
    """How one target reacts to its schedule."""

    schedule_enabled: bool = DEFAULT_SCHEDULE_ENABLED
    default_hvac_mode: str = DEFAULT_HVAC_MODE
    off_behavior: str = DEFAULT_OFF_BEHAVIOR
    apply_on_start: bool = DEFAULT_APPLY_ON_START

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> Self:
        """Return behaviour from stored options, filling in defaults."""
        data = _as_mapping(data)
        off_behavior = data.get(CONF_OFF_BEHAVIOR, DEFAULT_OFF_BEHAVIOR)
        mode = data.get(CONF_DEFAULT_HVAC_MODE, DEFAULT_HVAC_MODE)
        return cls(
            schedule_enabled=bool(
                data.get(CONF_SCHEDULE_ENABLED, DEFAULT_SCHEDULE_ENABLED)
            ),
            default_hvac_mode=(
                str(mode) if isinstance(mode, str) and mode else str(DEFAULT_HVAC_MODE)
            ),
            off_behavior=(
                off_behavior if off_behavior in OFF_BEHAVIORS else DEFAULT_OFF_BEHAVIOR
            ),
            apply_on_start=bool(data.get(CONF_APPLY_ON_START, DEFAULT_APPLY_ON_START)),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the stored representation."""
        return {
            CONF_SCHEDULE_ENABLED: self.schedule_enabled,
            CONF_DEFAULT_HVAC_MODE: self.default_hvac_mode,
            CONF_OFF_BEHAVIOR: self.off_behavior,
            CONF_APPLY_ON_START: self.apply_on_start,
        }


@dataclass(frozen=True, slots=True)
class PlanConfig:
    """One named schedule plan, holding a schedule helper per target."""

    id: str
    name: str
    icon: str | None = None
    min_outdoor_temp: float | None = None
    schedules: Mapping[str, str] = field(default_factory=lambda: EMPTY_MAPPING)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self | None:
        """Return a plan from stored options, or None when it is unusable."""
        plan_id = data.get(CONF_PLAN_ID)
        name = data.get(CONF_PLAN_NAME)
        if not isinstance(plan_id, str) or not plan_id:
            return None
        if not isinstance(name, str) or not name:
            return None
        icon = data.get(CONF_PLAN_ICON)
        schedules = {
            str(key): value
            for key, value in _as_mapping(data.get(CONF_PLAN_SCHEDULES)).items()
            if isinstance(value, str) and value
        }
        return cls(
            id=plan_id,
            name=name,
            icon=icon if isinstance(icon, str) and icon else None,
            min_outdoor_temp=_as_float(data.get(CONF_PLAN_MIN_OUTDOOR_TEMP)),
            schedules=MappingProxyType(schedules),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the stored representation."""
        data: dict[str, Any] = {
            CONF_PLAN_ID: self.id,
            CONF_PLAN_NAME: self.name,
            CONF_PLAN_SCHEDULES: dict(self.schedules),
        }
        if self.icon:
            data[CONF_PLAN_ICON] = self.icon
        if self.min_outdoor_temp is not None:
            data[CONF_PLAN_MIN_OUTDOOR_TEMP] = self.min_outdoor_temp
        return data

    def schedule_for(self, target_key: str) -> str | None:
        """Return the schedule helper entity id used for one target."""
        return self.schedules.get(target_key) or None

    def with_schedule(self, target_key: str, schedule_entity_id: str | None) -> Self:
        """Return a copy with one target's schedule helper set or cleared."""
        schedules = dict(self.schedules)
        if schedule_entity_id:
            schedules[target_key] = schedule_entity_id
        else:
            schedules.pop(target_key, None)
        return type(self)(
            id=self.id,
            name=self.name,
            icon=self.icon,
            min_outdoor_temp=self.min_outdoor_temp,
            schedules=MappingProxyType(schedules),
        )


@dataclass(frozen=True, slots=True)
class PlanSelectionConfig:
    """The rule that picks the active plan when the select is on Automatic."""

    mode: str = DEFAULT_PLAN_SELECTION_MODE
    outdoor_temp_entity_id: str | None = None
    hysteresis: float = DEFAULT_HYSTERESIS
    sustain_minutes: int = DEFAULT_SUSTAIN_MINUTES

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> Self:
        """Return plan selection settings from stored options."""
        data = _as_mapping(data)
        mode = data.get(CONF_PLAN_SELECTION_MODE, DEFAULT_PLAN_SELECTION_MODE)
        entity_id = data.get(CONF_OUTDOOR_TEMP_ENTITY_ID)
        hysteresis = _as_float(data.get(CONF_HYSTERESIS))
        sustain = _as_float(data.get(CONF_SUSTAIN_MINUTES))
        return cls(
            mode=mode if mode in PLAN_MODES else PLAN_MODE_MANUAL,
            outdoor_temp_entity_id=(
                entity_id if isinstance(entity_id, str) and entity_id else None
            ),
            hysteresis=(
                abs(hysteresis) if hysteresis is not None else DEFAULT_HYSTERESIS
            ),
            sustain_minutes=(
                int(sustain)
                if sustain is not None and sustain >= 0
                else DEFAULT_SUSTAIN_MINUTES
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the stored representation."""
        return {
            CONF_PLAN_SELECTION_MODE: self.mode,
            CONF_OUTDOOR_TEMP_ENTITY_ID: self.outdoor_temp_entity_id,
            CONF_HYSTERESIS: self.hysteresis,
            CONF_SUSTAIN_MINUTES: self.sustain_minutes,
        }

    @property
    def automatic_available(self) -> bool:
        """Return whether an automatic rule is configured and usable."""
        return (
            self.mode == PLAN_MODE_OUTDOOR_TEMP
            and self.outdoor_temp_entity_id is not None
        )


@dataclass(frozen=True, slots=True)
class OverrideConfig:
    """Bounds applied to temporary holds requested by any user."""

    default_minutes: int = DEFAULT_OVERRIDE_MINUTES
    max_minutes: int = DEFAULT_OVERRIDE_MAX_MINUTES

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> Self:
        """Return override bounds from stored options."""
        data = _as_mapping(data)
        maximum = _as_positive_int(
            data.get(CONF_OVERRIDE_MAX_MINUTES), DEFAULT_OVERRIDE_MAX_MINUTES
        )
        default = _as_positive_int(
            data.get(CONF_OVERRIDE_DEFAULT_MINUTES), DEFAULT_OVERRIDE_MINUTES
        )
        return cls(default_minutes=min(default, maximum), max_minutes=maximum)

    def as_dict(self) -> dict[str, Any]:
        """Return the stored representation."""
        return {
            CONF_OVERRIDE_DEFAULT_MINUTES: self.default_minutes,
            CONF_OVERRIDE_MAX_MINUTES: self.max_minutes,
        }

    def clamp_minutes(self, minutes: float) -> int:
        """Return a requested hold length clamped to the configured bounds."""
        return max(1, min(int(minutes), self.max_minutes))


@dataclass(frozen=True, slots=True)
class RoomConfig:
    """Everything one config entry configures, parsed once."""

    targets: tuple[TargetConfig, ...] = ()
    behaviors: Mapping[str, TargetBehavior] = field(
        default_factory=lambda: EMPTY_MAPPING
    )
    plans: tuple[PlanConfig, ...] = ()
    plan_selection: PlanSelectionConfig = field(default_factory=PlanSelectionConfig)
    override: OverrideConfig = field(default_factory=OverrideConfig)
    legacy_on_time: str | None = None
    legacy_off_time: str | None = None

    @classmethod
    def from_entry(cls, entry: ConfigEntry) -> Self:
        """Parse a config entry into its room configuration."""
        return cls.from_dicts(entry.data, entry.options)

    @classmethod
    def from_dicts(cls, data: Mapping[str, Any], options: Mapping[str, Any]) -> Self:
        """Parse raw entry data and options into a room configuration."""
        targets = tuple(
            target
            for raw in _as_items(data.get(CONF_TARGETS))
            if isinstance(raw, Mapping) and (target := TargetConfig.from_dict(raw))
        )
        raw_behaviors = _as_mapping(options.get(CONF_TARGETS))
        behaviors = {
            target.key: TargetBehavior.from_dict(raw_behaviors.get(target.key))
            for target in targets
        }
        plans = tuple(
            plan
            for raw in _as_items(options.get(CONF_PLANS))
            if isinstance(raw, Mapping) and (plan := PlanConfig.from_dict(raw))
        )
        legacy_on = options.get(CONF_LEGACY_ON_TIME)
        legacy_off = options.get(CONF_LEGACY_OFF_TIME)
        return cls(
            targets=targets,
            behaviors=MappingProxyType(behaviors),
            plans=plans,
            plan_selection=PlanSelectionConfig.from_dict(
                options.get(CONF_PLAN_SELECTION)
            ),
            override=OverrideConfig.from_dict(options.get(CONF_OVERRIDE)),
            legacy_on_time=legacy_on if isinstance(legacy_on, str) else None,
            legacy_off_time=legacy_off if isinstance(legacy_off, str) else None,
        )

    def target_by_key(self, key: str) -> TargetConfig | None:
        """Return one target by its stable key."""
        return next((target for target in self.targets if target.key == key), None)

    def target_by_entity_id(self, entity_id: str) -> TargetConfig | None:
        """Return one target by the climate entity it wraps."""
        return next(
            (target for target in self.targets if target.entity_id == entity_id), None
        )

    def behavior_for(self, key: str) -> TargetBehavior:
        """Return the behaviour configured for one target."""
        return self.behaviors.get(key) or TargetBehavior()

    def plan_by_id(self, plan_id: str | None) -> PlanConfig | None:
        """Return one plan by id."""
        if plan_id is None:
            return None
        return next((plan for plan in self.plans if plan.id == plan_id), None)

    def plan_by_name(self, name: str | None) -> PlanConfig | None:
        """Return one plan by its case-insensitive name."""
        if not name:
            return None
        folded = name.casefold()
        return next(
            (plan for plan in self.plans if plan.name.casefold() == folded), None
        )

    @property
    def plan_names(self) -> tuple[str, ...]:
        """Return the configured plan names in order."""
        return tuple(plan.name for plan in self.plans)

    @property
    def ordered_plans(self) -> tuple[PlanConfig, ...]:
        """Return plans ordered by outdoor temperature band, coldest first.

        Plans without a threshold form the base band and sort first, keeping
        their configured order so the fallback plan stays predictable.
        """
        return tuple(
            sorted(
                self.plans,
                key=lambda plan: (
                    plan.min_outdoor_temp is not None,
                    plan.min_outdoor_temp if plan.min_outdoor_temp is not None else 0.0,
                ),
            )
        )

    @property
    def legacy_schedule(self) -> dict[str, str] | None:
        """Return the pre-migration daily times still waiting to be converted."""
        if not self.legacy_on_time and not self.legacy_off_time:
            return None
        return {
            "on_time": self.legacy_on_time or "",
            "off_time": self.legacy_off_time or "",
        }


def targets_as_data(targets: Iterable[TargetConfig]) -> list[dict[str, str]]:
    """Return the stored representation of a target list."""
    return [target.as_dict() for target in targets]


def plans_as_options(plans: Iterable[PlanConfig]) -> list[dict[str, Any]]:
    """Return the stored representation of a plan list."""
    return [plan.as_dict() for plan in plans]


def behaviors_as_options(
    behaviors: Mapping[str, TargetBehavior],
) -> dict[str, dict[str, Any]]:
    """Return the stored representation of the per-target behaviour map."""
    return {key: behavior.as_dict() for key, behavior in behaviors.items()}


def build_options(
    *,
    behaviors: Mapping[str, TargetBehavior],
    plans: Sequence[PlanConfig],
    plan_selection: PlanSelectionConfig,
    override: OverrideConfig,
    legacy_on_time: str | None = None,
    legacy_off_time: str | None = None,
) -> dict[str, Any]:
    """Return a complete options payload for a config entry."""
    options: dict[str, Any] = {
        CONF_TARGETS: behaviors_as_options(behaviors),
        CONF_PLANS: plans_as_options(plans),
        CONF_PLAN_SELECTION: plan_selection.as_dict(),
        CONF_OVERRIDE: override.as_dict(),
    }
    if legacy_on_time:
        options[CONF_LEGACY_ON_TIME] = legacy_on_time
    if legacy_off_time:
        options[CONF_LEGACY_OFF_TIME] = legacy_off_time
    return options


def options_from_config(
    config: RoomConfig,
    *,
    behaviors: Mapping[str, TargetBehavior] | None = None,
    plans: Sequence[PlanConfig] | None = None,
    plan_selection: PlanSelectionConfig | None = None,
    override: OverrideConfig | None = None,
) -> dict[str, Any]:
    """Return an options payload with selected parts of a room replaced."""
    return build_options(
        behaviors=config.behaviors if behaviors is None else behaviors,
        plans=config.plans if plans is None else plans,
        plan_selection=(
            config.plan_selection if plan_selection is None else plan_selection
        ),
        override=config.override if override is None else override,
        legacy_on_time=config.legacy_on_time,
        legacy_off_time=config.legacy_off_time,
    )


def options_with_behavior(
    config: RoomConfig, target_key: str, behavior: TargetBehavior
) -> dict[str, Any]:
    """Return an options payload with one target's behaviour replaced."""
    behaviors = dict(config.behaviors)
    behaviors[target_key] = behavior
    return options_from_config(config, behaviors=behaviors)


def options_with_plan(config: RoomConfig, plan: PlanConfig) -> dict[str, Any]:
    """Return an options payload with one plan replaced, or appended."""
    plans = list(config.plans)
    for index, existing in enumerate(plans):
        if existing.id == plan.id:
            plans[index] = plan
            break
    else:
        plans.append(plan)
    return options_from_config(config, plans=plans)
