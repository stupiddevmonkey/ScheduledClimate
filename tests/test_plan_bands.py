"""Edge cases for outdoor-temperature plan bands and selection persistence.

The band maths in :meth:`PlanSelector._band_for` is the riskiest part of plan
resolution, so these tests pin down the awkward inputs (no thresholds, equal
thresholds, negative readings, a zero hysteresis) and check that a manual
selection survives a restart and copes with the selected plan being deleted.
"""

from __future__ import annotations

from homeassistant.components.climate import ATTR_HVAC_MODES, HVACMode
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scheduled_climate.const import (
    DOMAIN,
    PLAN_MODE_OUTDOOR_TEMP,
)
from custom_components.scheduled_climate.coordinator import RoomCoordinator
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
from custom_components.scheduled_climate.plan import PlanSelector

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
            ATTR_SUPPORTED_FEATURES: 0,
        },
    )


def _entry(
    *,
    plans: list[PlanConfig],
    hysteresis: float = 0.0,
    sustain_minutes: int = 0,
) -> MockConfigEntry:
    """Return a one-target room whose plan is chosen by the outdoor sensor."""
    target = TargetConfig(key=TARGET_KEY, entity_id=TARGET_ENTITY_ID, name="Mini split")
    return MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        version=3,
        data={"name": "Living Room", "targets": targets_as_data([target])},
        options=build_options(
            behaviors={TARGET_KEY: TargetBehavior()},
            plans=plans,
            plan_selection=PlanSelectionConfig(
                mode=PLAN_MODE_OUTDOOR_TEMP,
                outdoor_temp_entity_id=OUTDOOR_ENTITY_ID,
                hysteresis=hysteresis,
                sustain_minutes=sustain_minutes,
            ),
            override=OverrideConfig(),
        ),
    )


async def _setup(
    hass: HomeAssistant,
    *,
    plans: list[PlanConfig],
    hysteresis: float = 0.0,
    outdoor: str = "10",
) -> tuple[MockConfigEntry, RoomCoordinator]:
    """Set up a room with the given plans and initial outdoor reading."""
    _set_target(hass)
    hass.states.async_set(OUTDOOR_ENTITY_ID, outdoor)
    entry = _entry(plans=plans, hysteresis=hysteresis)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, hass.data[DOMAIN][entry.entry_id]


async def _report(hass: HomeAssistant, temperature: float) -> None:
    """Publish an outdoor reading and let the selector react."""
    hass.states.async_set(OUTDOOR_ENTITY_ID, str(temperature))
    await hass.async_block_till_done()


async def test_several_plans_without_a_threshold_use_the_first_as_base(
    hass: HomeAssistant,
) -> None:
    """Untresholded plans form the base band; the first one wins there."""
    _entry_obj, coordinator = await _setup(
        hass,
        plans=[
            PlanConfig(id="base-a", name="Base A"),
            PlanConfig(id="base-b", name="Base B"),
            PlanConfig(id="hot", name="Hot", min_outdoor_temp=18.0),
        ],
        outdoor="10",
    )

    assert coordinator.plans.active_plan is not None
    assert coordinator.plans.active_plan.name == "Base A"

    await _report(hass, 25)
    assert coordinator.plans.active_plan.name == "Hot"

    await _report(hass, 5)
    assert coordinator.plans.active_plan.name == "Base A"


async def test_equal_thresholds_prefer_the_later_plan(hass: HomeAssistant) -> None:
    """When two bands share a threshold the last configured one takes it."""
    _entry_obj, coordinator = await _setup(
        hass,
        plans=[
            PlanConfig(id="base", name="Base"),
            PlanConfig(id="warm", name="Warm", min_outdoor_temp=18.0),
            PlanConfig(id="hot", name="Hot", min_outdoor_temp=18.0),
        ],
        outdoor="10",
    )
    assert coordinator.plans.active_plan.name == "Base"

    await _report(hass, 20)
    assert coordinator.plans.active_plan.name == "Hot"

    await _report(hass, 5)
    assert coordinator.plans.active_plan.name == "Base"


async def test_negative_outdoor_temperatures_are_handled(
    hass: HomeAssistant,
) -> None:
    """A band threshold below zero selects correctly for cold readings."""
    _entry_obj, coordinator = await _setup(
        hass,
        plans=[
            PlanConfig(id="deep-cold", name="Deep cold"),
            PlanConfig(id="mild", name="Mild", min_outdoor_temp=-5.0),
        ],
        outdoor="-10",
    )
    assert coordinator.plans.active_plan.name == "Deep cold"

    await _report(hass, -3)
    assert coordinator.plans.active_plan.name == "Mild"

    await _report(hass, -20)
    assert coordinator.plans.active_plan.name == "Deep cold"


async def test_zero_hysteresis_switches_at_the_exact_threshold(
    hass: HomeAssistant,
) -> None:
    """With no hysteresis the boundary is the threshold itself."""
    _entry_obj, coordinator = await _setup(
        hass,
        plans=[
            PlanConfig(id="winter", name="Winter"),
            PlanConfig(id="summer", name="Summer", min_outdoor_temp=18.0),
        ],
        hysteresis=0.0,
        outdoor="10",
    )
    assert coordinator.plans.active_plan.name == "Winter"

    await _report(hass, 17.9)
    assert coordinator.plans.active_plan.name == "Winter"

    # Exactly at the threshold the upper band is entered.
    await _report(hass, 18.0)
    assert coordinator.plans.active_plan.name == "Summer"

    await _report(hass, 17.9)
    assert coordinator.plans.active_plan.name == "Winter"


async def test_manual_selection_survives_a_restart(hass: HomeAssistant) -> None:
    """A plan chosen by hand is still active after the entry reloads."""
    entry, coordinator = await _setup(
        hass,
        plans=[
            PlanConfig(id="winter", name="Winter"),
            PlanConfig(id="summer", name="Summer", min_outdoor_temp=18.0),
        ],
        outdoor="10",
    )
    # Automatic would pick Winter for 10 degrees; pin Summer by hand instead.
    await coordinator.async_select_plan("Summer")
    await hass.async_block_till_done()
    assert coordinator.plans.active_plan.name == "Summer"

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    reloaded = hass.data[DOMAIN][entry.entry_id]
    assert reloaded is not coordinator
    assert reloaded.plans.automatic is False
    assert reloaded.plans.active_plan is not None
    assert reloaded.plans.active_plan.name == "Summer"


async def test_removing_the_selected_plan_then_reloading_falls_back(
    hass: HomeAssistant,
) -> None:
    """Deleting the manually selected plan and reloading picks a survivor."""
    entry, coordinator = await _setup(
        hass,
        plans=[
            PlanConfig(id="winter", name="Winter"),
            PlanConfig(id="summer", name="Summer", min_outdoor_temp=18.0),
        ],
        outdoor="10",
    )
    await coordinator.async_select_plan("Summer")
    await hass.async_block_till_done()
    assert coordinator.plans.active_plan.name == "Summer"

    # Drop the selected plan. Updating options reloads the entry.
    room = RoomConfig.from_entry(entry)
    remaining = [plan for plan in room.plans if plan.name != "Summer"]
    hass.config_entries.async_update_entry(
        entry, options=options_from_config(room, plans=remaining)
    )
    await hass.async_block_till_done()

    reloaded = hass.data[DOMAIN][entry.entry_id]
    assert reloaded.plans.active_plan is not None
    assert reloaded.plans.active_plan.name == "Winter"


# ----------------------------------------------------------------------
# Restoring a stored selection
# ----------------------------------------------------------------------


async def _selector(
    hass: HomeAssistant, entry: MockConfigEntry
) -> tuple[PlanSelector, RoomConfig]:
    """Return an initialized selector for a bare (not set up) entry."""
    _set_target(hass)
    hass.states.async_set(OUTDOOR_ENTITY_ID, "10")
    entry.add_to_hass(hass)
    config = RoomConfig.from_entry(entry)
    selector = PlanSelector(hass, entry, config)
    await selector.async_initialize()
    return selector, config


async def test_a_stored_selection_for_a_deleted_plan_is_ignored(
    hass: HomeAssistant,
) -> None:
    """A plan deleted while stopped must not leave the room stuck.

    Options changes reload the whole config entry, so a selector is always
    rebuilt from storage against the new configuration. A stored selection
    naming a plan that no longer exists has to fall back to automatic rather
    than pin the room to a plan that can never resolve.
    """
    entry = _entry(
        plans=[
            PlanConfig(id="winter", name="Winter"),
            PlanConfig(id="summer", name="Summer", min_outdoor_temp=18.0),
        ]
    )
    selector, _config = await _selector(hass, entry)
    assert await selector.async_select("Summer") is True
    assert selector.automatic is False
    selector.async_shutdown()

    # The user deletes the selected plan; the entry reloads with a fresh
    # selector that reads the same store.
    trimmed = RoomConfig.from_dicts(
        entry.data,
        options_from_config(
            RoomConfig.from_entry(entry),
            plans=[PlanConfig(id="winter", name="Winter")],
        ),
    )
    rebuilt = PlanSelector(hass, entry, trimmed)
    await rebuilt.async_initialize()

    assert rebuilt.automatic is True
    assert rebuilt.active_plan is not None
    assert rebuilt.active_plan.name == "Winter"
    rebuilt.async_shutdown()


async def test_a_stored_selection_for_a_live_plan_is_restored(
    hass: HomeAssistant,
) -> None:
    """A manual selection survives the selector being rebuilt."""
    entry = _entry(
        plans=[
            PlanConfig(id="winter", name="Winter"),
            PlanConfig(id="summer", name="Summer", min_outdoor_temp=18.0),
        ]
    )
    selector, config = await _selector(hass, entry)
    await selector.async_select("Summer")
    selector.async_shutdown()

    rebuilt = PlanSelector(hass, entry, config)
    await rebuilt.async_initialize()

    assert rebuilt.automatic is False
    assert rebuilt.active_plan is not None
    assert rebuilt.active_plan.name == "Summer"
    rebuilt.async_shutdown()


async def test_a_deleted_pending_plan_never_commits(hass: HomeAssistant) -> None:
    """A candidate awaiting its sustain window cannot commit once deleted."""
    entry = _entry(
        plans=[
            PlanConfig(id="winter", name="Winter"),
            PlanConfig(id="summer", name="Summer", min_outdoor_temp=18.0),
        ],
        sustain_minutes=30,
    )
    selector, _config = await _selector(hass, entry)
    assert selector.active_plan is not None
    assert selector.active_plan.name == "Winter"

    # A warm reading makes Summer a pending candidate (not yet committed).
    hass.states.async_set(OUTDOOR_ENTITY_ID, "25")
    await hass.async_block_till_done()
    assert selector.active_plan.name == "Winter"
    assert selector._pending_id == "summer"

    # Shutting down cancels the sustain window, so the deleted plan can never
    # be committed by a timer that outlives the configuration.
    selector.async_shutdown()
    assert selector._pending_id is None
