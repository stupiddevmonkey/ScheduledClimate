"""Smoke test for the room coordinator wiring."""

from homeassistant.components.climate import (
    ATTR_HVAC_MODES,
    ATTR_TEMPERATURE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.schedule import DOMAIN as SCHEDULE_DOMAIN
from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scheduled_climate.const import (
    ATTR_ACTIVE_PLAN,
    ATTR_PLAN_OPTIONS,
    ATTR_PLAN_SCHEDULES,
    ATTR_ROOM_ENTITIES,
    ATTR_SCHEDULE_ENABLED,
    ATTR_SCHEDULE_ENTITY_ID,
    ATTR_TARGET_KEY,
    ATTR_TARGET_NAME,
    ATTR_TEMPERATURE_UNIT,
    CONF_TARGET_ENTITY_ID,
    DOMAIN,
    PLAN_MODE_OUTDOOR_TEMP,
    SERVICE_DISABLE_SCHEDULE,
)
from custom_components.scheduled_climate.diagnostics import (
    async_get_config_entry_diagnostics,
)
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
MINI_SPLIT_ENTITY_ID = "climate.mini_split"
RADIANT_ENTITY_ID = "climate.radiant_heater"
MINI_SPLIT_KEY = "mini-split"
RADIANT_KEY = "radiant"


def _set_target(hass: HomeAssistant, entity_id: str = TARGET_ENTITY_ID) -> None:
    """Publish a minimal climate target state."""
    hass.states.async_set(
        entity_id,
        HVACMode.HEAT,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT],
            ATTR_TEMPERATURE: 21.5,
            ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.TARGET_TEMPERATURE,
        },
    )


def _room_entry(*, plans: list[PlanConfig]) -> MockConfigEntry:
    """Return a two-target room entry at the current schema version."""
    targets = [
        TargetConfig(
            key=MINI_SPLIT_KEY, entity_id=MINI_SPLIT_ENTITY_ID, name="Mini split"
        ),
        TargetConfig(
            key=RADIANT_KEY, entity_id=RADIANT_ENTITY_ID, name="Radiant heater"
        ),
    ]
    return MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        version=3,
        data={"name": "Living Room", "targets": targets_as_data(targets)},
        options=build_options(
            behaviors={
                MINI_SPLIT_KEY: TargetBehavior(
                    schedule_enabled=True, apply_on_start=False
                ),
                RADIANT_KEY: TargetBehavior(
                    schedule_enabled=True, apply_on_start=False
                ),
            },
            plans=plans,
            plan_selection=PlanSelectionConfig(),
            override=OverrideConfig(),
        ),
    )


async def test_legacy_entry_becomes_a_room(hass: HomeAssistant) -> None:
    """A version 1 entry migrates into a room and keeps its unique id."""
    _set_target(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        version=1,
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID, "name": "Living Room"},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 3
    assert entry.data["targets"] == [
        {
            "key": entry.entry_id,
            "target_entity_id": TARGET_ENTITY_ID,
            "name": "Living Room",
        }
    ]

    registry = er.async_get(hass)
    wrapper_entity_id = registry.async_get_entity_id("climate", DOMAIN, entry.entry_id)
    assert wrapper_entity_id is not None

    state = hass.states.get(wrapper_entity_id)
    assert state is not None
    assert state.attributes[ATTR_TARGET_KEY] == entry.entry_id
    assert state.attributes[ATTR_ROOM_ENTITIES] == [wrapper_entity_id]
    assert state.attributes[ATTR_PLAN_OPTIONS] == ["Default"]
    assert state.attributes[ATTR_ACTIVE_PLAN] == "Default"

    select_entity_id = registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.entry_id}_plan"
    )
    assert select_entity_id is not None
    select_state = hass.states.get(select_entity_id)
    assert select_state is not None
    assert select_state.state == "Default"


async def test_room_controls_several_climate_entities(
    hass: HomeAssistant,
) -> None:
    """A room creates one wrapper entity per target, sharing one device."""
    _set_target(hass, MINI_SPLIT_ENTITY_ID)
    _set_target(hass, RADIANT_ENTITY_ID)
    assert await async_setup_component(
        hass,
        SCHEDULE_DOMAIN,
        {
            SCHEDULE_DOMAIN: {
                "mini_split_winter": {
                    "name": "Mini split winter",
                    "monday": [{"from": "07:00:00", "to": "09:00:00"}],
                },
                "radiant_winter": {
                    "name": "Radiant winter",
                    "monday": [{"from": "06:00:00", "to": "08:00:00"}],
                },
            }
        },
    )
    await hass.async_block_till_done()

    entry = _room_entry(
        plans=[
            PlanConfig(
                id="winter",
                name="Winter",
                schedules={
                    MINI_SPLIT_KEY: "schedule.mini_split_winter",
                    RADIANT_KEY: "schedule.radiant_winter",
                },
            ),
            PlanConfig(id="summer", name="Summer"),
        ]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    mini_split = registry.async_get_entity_id("climate", DOMAIN, MINI_SPLIT_KEY)
    radiant = registry.async_get_entity_id("climate", DOMAIN, RADIANT_KEY)
    assert mini_split is not None
    assert radiant is not None
    assert mini_split != radiant

    devices = {
        registry.async_get(entity_id).device_id for entity_id in (mini_split, radiant)
    }
    assert len(devices) == 1

    mini_split_state = hass.states.get(mini_split)
    radiant_state = hass.states.get(radiant)
    assert mini_split_state.attributes[ATTR_ROOM_ENTITIES] == [mini_split, radiant]
    assert radiant_state.attributes[ATTR_ROOM_ENTITIES] == [mini_split, radiant]

    # The short target name is published so the card does not have to strip the
    # room prefix out of friendly_name.
    assert mini_split_state.attributes[ATTR_TARGET_NAME] == "Mini split"
    assert radiant_state.attributes[ATTR_TARGET_NAME] == "Radiant heater"
    assert mini_split_state.attributes[ATTR_FRIENDLY_NAME] == "Living Room Mini split"

    # Each target follows its own helper for the active plan.
    assert (
        mini_split_state.attributes[ATTR_SCHEDULE_ENTITY_ID]
        == "schedule.mini_split_winter"
    )
    assert (
        radiant_state.attributes[ATTR_SCHEDULE_ENTITY_ID] == "schedule.radiant_winter"
    )

    # Every plan is advertised, with the helper id the card needs to edit it.
    assert mini_split_state.attributes[ATTR_PLAN_OPTIONS] == ["Winter", "Summer"]
    assert mini_split_state.attributes[ATTR_PLAN_SCHEDULES] == {
        "Winter": "mini_split_winter",
        "Summer": None,
    }
    assert radiant_state.attributes[ATTR_PLAN_SCHEDULES] == {
        "Winter": "radiant_winter",
        "Summer": None,
    }


async def test_switching_plan_repoints_every_target(hass: HomeAssistant) -> None:
    """Choosing another plan moves all targets onto its helpers at once."""
    _set_target(hass, MINI_SPLIT_ENTITY_ID)
    _set_target(hass, RADIANT_ENTITY_ID)
    entry = _room_entry(
        plans=[
            PlanConfig(
                id="winter",
                name="Winter",
                schedules={
                    MINI_SPLIT_KEY: "schedule.mini_split_winter",
                    RADIANT_KEY: "schedule.radiant_winter",
                },
            ),
            PlanConfig(
                id="summer",
                name="Summer",
                schedules={MINI_SPLIT_KEY: "schedule.mini_split_summer"},
            ),
        ]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_select_plan("Summer")
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    mini_split = registry.async_get_entity_id("climate", DOMAIN, MINI_SPLIT_KEY)
    radiant = registry.async_get_entity_id("climate", DOMAIN, RADIANT_KEY)

    mini_split_state = hass.states.get(mini_split)
    radiant_state = hass.states.get(radiant)
    assert mini_split_state.attributes[ATTR_ACTIVE_PLAN] == "Summer"
    assert (
        mini_split_state.attributes[ATTR_SCHEDULE_ENTITY_ID]
        == "schedule.mini_split_summer"
    )
    # The radiant heater has no helper in the summer plan, so it stands down.
    assert radiant_state.attributes[ATTR_ACTIVE_PLAN] == "Summer"
    assert radiant_state.attributes[ATTR_SCHEDULE_ENTITY_ID] is None
    assert radiant_state.attributes[ATTR_SCHEDULE_ENABLED] is False


async def test_disabling_one_target_leaves_the_other_running(
    hass: HomeAssistant,
) -> None:
    """Pausing the schedule is scoped to the target it is aimed at."""
    _set_target(hass, MINI_SPLIT_ENTITY_ID)
    _set_target(hass, RADIANT_ENTITY_ID)
    entry = _room_entry(
        plans=[
            PlanConfig(
                id="winter",
                name="Winter",
                schedules={
                    MINI_SPLIT_KEY: "schedule.mini_split_winter",
                    RADIANT_KEY: "schedule.radiant_winter",
                },
            )
        ]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    mini_split = registry.async_get_entity_id("climate", DOMAIN, MINI_SPLIT_KEY)
    radiant = registry.async_get_entity_id("climate", DOMAIN, RADIANT_KEY)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_DISABLE_SCHEDULE,
        {"entity_id": mini_split},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(mini_split).attributes[ATTR_SCHEDULE_ENABLED] is False
    assert hass.states.get(radiant).attributes[ATTR_SCHEDULE_ENABLED] is True


async def test_diagnostics_describe_the_whole_room(hass: HomeAssistant) -> None:
    """Diagnostics report every target and plan in the room."""
    _set_target(hass, MINI_SPLIT_ENTITY_ID)
    _set_target(hass, RADIANT_ENTITY_ID)
    entry = _room_entry(
        plans=[
            PlanConfig(
                id="winter",
                name="Winter",
                schedules={MINI_SPLIT_KEY: "schedule.mini_split_winter"},
            ),
            PlanConfig(id="summer", name="Summer", min_outdoor_temp=18.0),
        ]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    report = await async_get_config_entry_diagnostics(hass, entry)

    assert report["entry"]["version"] == 3
    assert report["plan"]["active_plan"] == "Winter"
    assert [plan["name"] for plan in report["plan"]["plans"]] == ["Winter", "Summer"]
    assert [target["key"] for target in report["targets"]] == [
        MINI_SPLIT_KEY,
        RADIANT_KEY,
    ]
    assert report["targets"][0]["schedule"]["entity_id"] == "schedule.mini_split_winter"
    assert report["targets"][1]["schedule"]["entity_id"] is None
    assert report["targets"][0]["override"] is None


OUTDOOR_ENTITY_ID = "sensor.outdoor_temperature"


def _capture_climate_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Record every climate service call in order."""
    calls: list[ServiceCall] = []

    async def handler(call: ServiceCall) -> None:
        calls.append(call)

    for service in (SERVICE_SET_HVAC_MODE, SERVICE_SET_TEMPERATURE):
        hass.services.async_register(CLIMATE_DOMAIN, service, handler)
    return calls


async def test_unload_stops_every_listener_and_callback(
    hass: HomeAssistant,
) -> None:
    """After unload, sensor and schedule changes must not touch the target."""
    _set_target(hass, MINI_SPLIT_ENTITY_ID)
    hass.states.async_set(OUTDOOR_ENTITY_ID, "10")
    hass.states.async_set(
        "schedule.mini_split_winter", STATE_ON, {ATTR_TEMPERATURE: 21}
    )

    target = TargetConfig(
        key=MINI_SPLIT_KEY, entity_id=MINI_SPLIT_ENTITY_ID, name="Mini split"
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        version=3,
        data={"name": "Living Room", "targets": targets_as_data([target])},
        options=build_options(
            behaviors={
                MINI_SPLIT_KEY: TargetBehavior(
                    schedule_enabled=True, apply_on_start=False
                )
            },
            plans=[
                PlanConfig(
                    id="winter",
                    name="Winter",
                    schedules={MINI_SPLIT_KEY: "schedule.mini_split_winter"},
                )
            ],
            plan_selection=PlanSelectionConfig(
                mode=PLAN_MODE_OUTDOOR_TEMP,
                outdoor_temp_entity_id=OUTDOOR_ENTITY_ID,
            ),
            override=OverrideConfig(),
        ),
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data[DOMAIN]

    # Any lingering listener would fire a climate service on these changes.
    calls = _capture_climate_calls(hass)
    hass.states.async_set(OUTDOOR_ENTITY_ID, "30")
    hass.states.async_set(
        "schedule.mini_split_winter", STATE_ON, {ATTR_TEMPERATURE: 25}
    )
    await hass.async_block_till_done()
    hass.states.async_set("schedule.mini_split_winter", STATE_OFF)
    await hass.async_block_till_done()

    assert calls == []
