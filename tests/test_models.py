"""Tests for parsing stored room configuration."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.scheduled_climate.models import (
    OverrideConfig,
    PlanConfig,
    PlanSelectionConfig,
    RoomConfig,
    TargetBehavior,
    TargetConfig,
    build_options,
    options_from_config,
    targets_as_data,
)

TARGET_KEY = "target-1"


def _valid() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a well formed data and options pair."""
    target = TargetConfig(
        key=TARGET_KEY, entity_id="climate.mini_split", name="Mini split"
    )
    data = {"name": "Living Room", "targets": targets_as_data([target])}
    options = build_options(
        behaviors={TARGET_KEY: TargetBehavior(schedule_enabled=True)},
        plans=[
            PlanConfig(
                id="winter", name="Winter", schedules={TARGET_KEY: "schedule.winter"}
            )
        ],
        plan_selection=PlanSelectionConfig(),
        override=OverrideConfig(),
    )
    return data, options


def test_round_trip_preserves_everything() -> None:
    """A built options payload parses back into the same room."""
    data, options = _valid()
    room = RoomConfig.from_dicts(data, options)

    assert [target.key for target in room.targets] == [TARGET_KEY]
    assert room.behavior_for(TARGET_KEY).schedule_enabled is True
    assert room.plan_names == ("Winter",)
    assert room.plans[0].schedule_for(TARGET_KEY) == "schedule.winter"

    again = RoomConfig.from_dicts(data, options_from_config(room))
    assert again == room


@pytest.mark.parametrize(
    "mutate",
    [
        # The behaviour map given the list shape that entry.data uses.
        lambda data, options: options.update({"targets": [{"key": TARGET_KEY}]}),
        # A single behaviour corrupted to a truthy scalar.
        lambda data, options: options.update({"targets": {TARGET_KEY: "heat"}}),
        # Whole sections replaced by the wrong type.
        lambda data, options: options.update({"targets": "nonsense"}),
        lambda data, options: options.update({"plans": {"winter": {}}}),
        lambda data, options: options.update({"plans": 5}),
        lambda data, options: options.update({"plan_selection": "manual"}),
        lambda data, options: options.update({"override": []}),
        lambda data, options: data.update({"targets": "nonsense"}),
        lambda data, options: data.update({"targets": [None, 7, "x"]}),
        lambda data, options: data.update({"targets": None}),
    ],
)
def test_corrupt_options_degrade_instead_of_raising(mutate: Any) -> None:
    """Hand-edited or half-migrated storage must never break parsing.

    A config entry that cannot be parsed would also break the options flow
    that exists to repair it, so every field falls back to a default.
    """
    data, options = _valid()
    mutate(data, options)

    room = RoomConfig.from_dicts(data, options)

    # Whatever survived, the result is a usable RoomConfig with sane defaults.
    assert isinstance(room.plan_selection, PlanSelectionConfig)
    assert isinstance(room.override, OverrideConfig)
    assert room.override.max_minutes >= 1
    assert room.behavior_for("missing-key") == TargetBehavior()
    assert room.plan_by_id("nope") is None
    assert room.plan_by_name("nope") is None


def test_corrupt_plan_schedules_are_dropped() -> None:
    """A plan whose schedule map is corrupt keeps its name and loses the link."""
    data, options = _valid()
    options["plans"] = [{"id": "winter", "name": "Winter", "schedules": "broken"}]

    room = RoomConfig.from_dicts(data, options)

    assert room.plan_names == ("Winter",)
    assert room.plans[0].schedule_for(TARGET_KEY) is None


def test_plans_without_a_threshold_sort_before_the_bands() -> None:
    """Ordering puts the base band first and then ascending thresholds."""
    room = RoomConfig(
        plans=(
            PlanConfig(id="c", name="Hot", min_outdoor_temp=25.0),
            PlanConfig(id="a", name="Base"),
            PlanConfig(id="b", name="Warm", min_outdoor_temp=18.0),
        )
    )
    assert [plan.name for plan in room.ordered_plans] == ["Base", "Warm", "Hot"]
