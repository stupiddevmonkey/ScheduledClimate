"""Tests for upper-bounded and windowed plan bands.

A plan can name a lower bound, an upper bound, both, or neither. These tests
pin down the cases the original "at or above" only model could not express:
a cold-weather plan, a plan limited to a band, and the precedence between
overlapping bands.
"""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.scheduled_climate.models import (
    PlanConfig,
    PlanSelectionConfig,
    RoomConfig,
)
from custom_components.scheduled_climate.plan import PlanSelector

FROST = PlanConfig(id="frost", name="Frost", max_outdoor_temp=2.0)
WINTER = PlanConfig(id="winter", name="Winter")
SUMMER = PlanConfig(id="summer", name="Summer", min_outdoor_temp=18.0)
SHOULDER = PlanConfig(
    id="shoulder", name="Shoulder", min_outdoor_temp=8.0, max_outdoor_temp=16.0
)


def _resolve(
    hass: HomeAssistant,
    plans: list[PlanConfig],
    temperature: float,
    *,
    current: PlanConfig | None = None,
    hysteresis: float = 0.0,
) -> str | None:
    """Return the plan a reading resolves to, without any Home Assistant wiring."""
    config = RoomConfig(
        plans=tuple(plans),
        plan_selection=PlanSelectionConfig(hysteresis=hysteresis),
    )
    selector = PlanSelector.__new__(PlanSelector)
    selector._config = config
    selector._resolved_id = current.id if current else None
    plan = selector._band_for(temperature)
    return plan.name if plan else None


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [
        (-5.0, "Frost"),
        (1.9, "Frost"),
        (2.0, "Winter"),
        (10.0, "Winter"),
        (25.0, "Summer"),
    ],
)
async def test_a_cold_weather_plan_activates_below_its_bound(
    hass: HomeAssistant, temperature: float, expected: str
) -> None:
    """An upper bound expresses "use this plan when it is colder than X"."""
    assert _resolve(hass, [FROST, WINTER, SUMMER], temperature) == expected


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [
        (5.0, "Winter"),
        (8.0, "Shoulder"),
        (15.9, "Shoulder"),
        (16.0, "Winter"),
        (20.0, "Summer"),
    ],
)
async def test_a_window_plan_only_covers_its_band(
    hass: HomeAssistant, temperature: float, expected: str
) -> None:
    """Naming both bounds limits a plan to that band, half open at the top."""
    assert _resolve(hass, [WINTER, SUMMER, SHOULDER], temperature) == expected


async def test_a_window_beats_a_single_sided_band(hass: HomeAssistant) -> None:
    """The most specific band wins where two overlap."""
    overlapping = PlanConfig(id="mild", name="Mild", min_outdoor_temp=10.0)
    # At 12 both Mild (>=10) and Shoulder (8-16) match; the window is tighter.
    assert _resolve(hass, [WINTER, overlapping, SHOULDER], 12.0) == "Shoulder"


async def test_a_bounded_plan_beats_the_unbounded_fallback(
    hass: HomeAssistant,
) -> None:
    """The plan with no bounds only applies when nothing else matches."""
    assert _resolve(hass, [WINTER, FROST], -10.0) == "Frost"
    assert _resolve(hass, [WINTER, FROST], 10.0) == "Winter"


@pytest.mark.parametrize(
    ("temperature", "current", "expected"),
    [
        # Entering Frost needs the reading clearly below its bound.
        (1.5, WINTER, "Winter"),
        (1.0, WINTER, "Winter"),
        (0.9, WINTER, "Frost"),
        # Leaving Frost needs the reading clearly above it. The band is half
        # open, so the widened edge at 3.0 is itself outside the band.
        (2.5, FROST, "Frost"),
        (2.9, FROST, "Frost"),
        (3.0, FROST, "Winter"),
    ],
)
async def test_hysteresis_applies_to_an_upper_bound(
    hass: HomeAssistant,
    temperature: float,
    current: PlanConfig,
    expected: str,
) -> None:
    """The dead zone straddles an upper bound just as it does a lower one.

    Frost ends at 2 degrees with a hysteresis of 2, so the dead zone is
    ``[1, 3)``: the plan is entered below 1 and left at 3, mirroring the
    ``[17, 19)`` zone a lower bound of 18 produces.
    """
    assert (
        _resolve(
            hass,
            [FROST, WINTER],
            temperature,
            current=current,
            hysteresis=2.0,
        )
        == expected
    )


async def test_a_gap_between_bands_holds_the_current_plan(
    hass: HomeAssistant,
) -> None:
    """Plans that leave a gap must not drop the room's schedule."""
    cold = PlanConfig(id="cold", name="Cold", max_outdoor_temp=5.0)
    hot = PlanConfig(id="hot", name="Hot", min_outdoor_temp=20.0)

    # 12 degrees falls in the gap; the plan in force simply stays.
    assert _resolve(hass, [cold, hot], 12.0, current=cold) == "Cold"
    assert _resolve(hass, [cold, hot], 12.0, current=hot) == "Hot"

    # With no plan yet resolved, the nearest band is used rather than nothing.
    assert _resolve(hass, [cold, hot], 6.0) == "Cold"
    assert _resolve(hass, [cold, hot], 19.0) == "Hot"


async def test_bounds_round_trip_through_storage(hass: HomeAssistant) -> None:
    """Both bounds survive being written to and read back from options."""
    stored = SHOULDER.as_dict()
    assert stored["min_outdoor_temp"] == 8.0
    assert stored["max_outdoor_temp"] == 16.0

    restored = PlanConfig.from_dict(stored)
    assert restored is not None
    assert restored.min_outdoor_temp == 8.0
    assert restored.max_outdoor_temp == 16.0
    assert restored.bounded is True

    # A plan with no bounds stores neither key and is not bounded.
    assert "min_outdoor_temp" not in WINTER.as_dict()
    assert "max_outdoor_temp" not in WINTER.as_dict()
    assert WINTER.bounded is False


async def test_match_order_is_most_specific_first(hass: HomeAssistant) -> None:
    """Windows come first, then lower bounds, then upper bounds, then the base."""
    room = RoomConfig(plans=(WINTER, SUMMER, FROST, SHOULDER))
    assert [plan.name for plan in room.match_order] == [
        "Shoulder",
        "Summer",
        "Frost",
        "Winter",
    ]
