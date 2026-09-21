"""Tests for outdoor-temperature plan selection."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from homeassistant.components.climate import (
    ATTR_HVAC_MODES,
    ATTR_TEMPERATURE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_SUPPORTED_FEATURES, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.scheduled_climate.const import (
    ATTR_ACTIVE_PLAN,
    ATTR_TEMPERATURE_UNIT,
    DOMAIN,
    ISSUE_OUTDOOR_SENSOR_UNAVAILABLE,
    PLAN_AUTOMATIC,
    PLAN_MODE_OUTDOOR_TEMP,
)
from custom_components.scheduled_climate.coordinator import RoomCoordinator
from custom_components.scheduled_climate.models import (
    OverrideConfig,
    PlanConfig,
    PlanSelectionConfig,
    TargetBehavior,
    TargetConfig,
    build_options,
    targets_as_data,
)

TARGET_ENTITY_ID = "climate.living_room"
OUTDOOR_ENTITY_ID = "sensor.outdoor_temperature"
TARGET_KEY = "target-1"


def _set_target(hass: HomeAssistant) -> None:
    """Publish a minimal climate target state."""
    hass.states.async_set(
        TARGET_ENTITY_ID,
        HVACMode.HEAT,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL],
            ATTR_TEMPERATURE: 21.5,
            ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.TARGET_TEMPERATURE,
        },
    )


async def _setup_room(
    hass: HomeAssistant,
    *,
    sustain_minutes: int = 0,
    hysteresis: float = 2.0,
    outdoor: str | None = "10",
) -> tuple[MockConfigEntry, RoomCoordinator]:
    """Set up a room with a cold-weather and a warm-weather plan."""
    _set_target(hass)
    if outdoor is not None:
        hass.states.async_set(OUTDOOR_ENTITY_ID, outdoor)

    target = TargetConfig(key=TARGET_KEY, entity_id=TARGET_ENTITY_ID, name="Mini split")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        version=3,
        data={"name": "Living Room", "targets": targets_as_data([target])},
        options=build_options(
            behaviors={TARGET_KEY: TargetBehavior()},
            plans=[
                PlanConfig(id="winter", name="Winter"),
                PlanConfig(id="summer", name="Summer", min_outdoor_temp=18.0),
            ],
            plan_selection=PlanSelectionConfig(
                mode=PLAN_MODE_OUTDOOR_TEMP,
                outdoor_temp_entity_id=OUTDOOR_ENTITY_ID,
                hysteresis=hysteresis,
                sustain_minutes=sustain_minutes,
            ),
            override=OverrideConfig(),
        ),
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, hass.data[DOMAIN][entry.entry_id]


async def _report(hass: HomeAssistant, temperature: float) -> None:
    """Publish an outdoor reading and let the selector react."""
    hass.states.async_set(OUTDOOR_ENTITY_ID, str(temperature))
    await hass.async_block_till_done()


async def test_bands_pick_the_plan_for_the_reading(hass: HomeAssistant) -> None:
    """A cold reading selects the base plan, a warm one the upper band."""
    _entry, coordinator = await _setup_room(hass)
    assert coordinator.plans.active_plan is not None
    assert coordinator.plans.active_plan.name == "Winter"

    await _report(hass, 25)
    assert coordinator.plans.active_plan.name == "Summer"

    await _report(hass, 5)
    assert coordinator.plans.active_plan.name == "Winter"


@pytest.mark.parametrize(
    ("readings", "expected"),
    [
        # Moving up needs the threshold plus half the hysteresis.
        ([18.0], "Winter"),
        ([18.9], "Winter"),
        ([19.0], "Summer"),
        # Once on Summer, it holds until half the hysteresis below.
        ([19.0, 17.5], "Summer"),
        ([19.0, 17.0], "Summer"),
        ([19.0, 16.9], "Winter"),
    ],
)
async def test_hysteresis_stops_flapping(
    hass: HomeAssistant, readings: list[float], expected: str
) -> None:
    """The active band holds until the reading clears it by half the width."""
    _entry, coordinator = await _setup_room(hass)
    for reading in readings:
        await _report(hass, reading)

    assert coordinator.plans.active_plan is not None
    assert coordinator.plans.active_plan.name == expected


async def test_sustain_delay_ignores_brief_excursions(
    hass: HomeAssistant,
) -> None:
    """A candidate must hold for the sustain window before it commits."""
    _entry, coordinator = await _setup_room(hass, sustain_minutes=30)
    assert coordinator.plans.active_plan.name == "Winter"

    await _report(hass, 25)
    assert coordinator.plans.active_plan.name == "Winter"

    # The reading falls back before the window elapses.
    await _report(hass, 5)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert coordinator.plans.active_plan.name == "Winter"

    # A reading that holds for the whole window does switch the plan.
    await _report(hass, 25)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert coordinator.plans.active_plan.name == "Summer"


async def test_unusable_sensor_holds_the_last_plan(hass: HomeAssistant) -> None:
    """An unavailable sensor keeps the current plan and raises a repair."""
    entry, coordinator = await _setup_room(hass)
    await _report(hass, 25)
    assert coordinator.plans.active_plan.name == "Summer"

    hass.states.async_set(OUTDOOR_ENTITY_ID, "unavailable")
    await hass.async_block_till_done()

    assert coordinator.plans.active_plan.name == "Summer"
    assert coordinator.plans.outdoor_temperature is None

    issue_registry = hass.data["issue_registry"]
    assert issue_registry.async_get_issue(
        DOMAIN, f"{ISSUE_OUTDOOR_SENSOR_UNAVAILABLE}_{entry.entry_id}"
    )


async def test_manual_selection_is_sticky(hass: HomeAssistant) -> None:
    """Picking a plan by hand stops the sensor from changing it."""
    _entry, coordinator = await _setup_room(hass)

    await coordinator.async_select_plan("Summer")
    assert coordinator.plans.active_plan.name == "Summer"
    assert coordinator.plans.automatic is False

    await _report(hass, -5)
    assert coordinator.plans.active_plan.name == "Summer"

    await coordinator.async_select_plan(PLAN_AUTOMATIC)
    assert coordinator.plans.automatic is True
    assert coordinator.plans.active_plan.name == "Winter"


async def test_unknown_plan_is_rejected(hass: HomeAssistant) -> None:
    """Selecting a plan that does not exist raises."""
    _entry, coordinator = await _setup_room(hass)
    with pytest.raises(ValueError):
        await coordinator.async_select_plan("Autumn")


async def test_select_entity_exposes_the_plans(hass: HomeAssistant) -> None:
    """The select entity offers Automatic plus every plan name."""
    entry, coordinator = await _setup_room(hass)
    entity_id = er.async_get(hass).async_get_entity_id(
        "select", DOMAIN, f"{entry.entry_id}_plan"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes["options"] == [PLAN_AUTOMATIC, "Winter", "Summer"]
    assert state.state == PLAN_AUTOMATIC

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": "Summer"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "Summer"
    assert coordinator.plans.active_plan.name == "Summer"


async def test_plan_change_repoints_the_wrapper_entity(
    hass: HomeAssistant,
) -> None:
    """Switching plans changes which schedule helper a target follows."""
    entry, coordinator = await _setup_room(hass)
    registry = er.async_get(hass)
    wrapper_entity_id = registry.async_get_entity_id("climate", DOMAIN, TARGET_KEY)
    assert wrapper_entity_id is not None

    attributes: dict[str, Any] = hass.states.get(wrapper_entity_id).attributes
    assert attributes[ATTR_ACTIVE_PLAN] == "Winter"

    await coordinator.async_select_plan("Summer")
    await hass.async_block_till_done()

    attributes = hass.states.get(wrapper_entity_id).attributes
    assert attributes[ATTR_ACTIVE_PLAN] == "Summer"
    assert entry.version == 3
