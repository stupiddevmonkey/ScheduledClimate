"""Tests for the Scheduled Climate wrapper entities."""

from datetime import timedelta

import pytest
import voluptuous as vol
from conftest import make_room_entry, make_target, set_target_state
from homeassistant.components.climate import (
    ATTR_HVAC_MODES,
    ATTR_SWING_HORIZONTAL_MODE,
    ATTR_SWING_HORIZONTAL_MODES,
    ATTR_TEMPERATURE,
    DATA_COMPONENT,
    SERVICE_SET_SWING_HORIZONTAL_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.schedule import DOMAIN as SCHEDULE_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_UNAVAILABLE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.scheduled_climate.climate import ScheduledClimateEntity
from custom_components.scheduled_climate.const import (
    ATTR_ACTIVE_PLAN,
    ATTR_ACTIVE_SCHEDULE_BLOCK,
    ATTR_DURATION,
    ATTR_LEGACY_SCHEDULE,
    ATTR_NEXT_SCHEDULE_EVENT,
    ATTR_OVERRIDE_ACTIVE,
    ATTR_OVERRIDE_BLOCK,
    ATTR_OVERRIDE_UNTIL,
    ATTR_PLAN,
    ATTR_PLAN_OPTIONS,
    ATTR_PLAN_RESOLVED_AUTOMATICALLY,
    ATTR_PLAN_SCHEDULES,
    ATTR_PLAN_SELECTION_MODE,
    ATTR_ROOM_ENTITIES,
    ATTR_SCHEDULE_ACTIVE,
    ATTR_SCHEDULE_ENABLED,
    ATTR_SCHEDULE_ENTITY_ID,
    ATTR_SCHEDULE_ID,
    ATTR_SCHEDULE_ISSUES,
    ATTR_TARGET_KEY,
    ATTR_TEMPERATURE_UNIT,
    ATTR_TIMER_ACTION,
    ATTR_TIMER_DEADLINE,
    ATTR_UNTIL_NEXT_BLOCK,
    DOMAIN,
    PLAN_MODE_MANUAL,
    SERVICE_CANCEL_TIMER,
    SERVICE_CLEAR_OVERRIDE,
    SERVICE_DISABLE_SCHEDULE,
    SERVICE_ENABLE_SCHEDULE,
    SERVICE_LINK_SCHEDULE,
    SERVICE_SELECT_PLAN,
    SERVICE_SET_OVERRIDE,
    SERVICE_START_OFF_TIMER,
    SERVICE_START_ON_TIMER,
)
from custom_components.scheduled_climate.models import (
    PlanConfig,
    RoomConfig,
    TargetBehavior,
)

LIVING_ROOM = "climate.living_room"
BEDROOM = "climate.bedroom"
LIVING_KEY = "living-room-key"
BEDROOM_KEY = "bedroom-key"


class _TargetClimate(ClimateEntity):
    """Minimal climate target for end-to-end service tests."""

    _attr_name = "Living Room"
    _attr_unique_id = "living-room-target"
    _attr_hvac_mode = HVACMode.HEAT
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature = 21.5
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self) -> None:
        self.temperature_calls: list[dict[str, object]] = []

    async def async_set_temperature(self, **kwargs: object) -> None:
        """Record a target temperature service call."""
        self.temperature_calls.append(kwargs)


def _wrapper_id(hass: HomeAssistant, key: str) -> str:
    """Return the wrapper climate entity id for a target key."""
    entity_id = er.async_get(hass).async_get_entity_id(CLIMATE_DOMAIN, DOMAIN, key)
    assert entity_id is not None
    return entity_id


async def _setup_schedule_helper(hass: HomeAssistant) -> None:
    """Set up a schedule helper used to drive the wrapper."""
    assert await async_setup_component(
        hass,
        SCHEDULE_DOMAIN,
        {
            SCHEDULE_DOMAIN: {
                "office": {
                    "name": "Office",
                    "monday": [{"from": "07:00:00", "to": "09:00:00"}],
                }
            }
        },
    )
    await hass.async_block_till_done()


async def test_mirrors_state_and_forwards_temperature(hass: HomeAssistant) -> None:
    """Test target state mirroring and the diagnostic attributes."""
    hass.states.async_set(
        LIVING_ROOM,
        HVACMode.HEAT,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT],
            ATTR_TEMPERATURE: 21.5,
            ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
            ATTR_SWING_HORIZONTAL_MODE: "on",
            ATTR_SWING_HORIZONTAL_MODES: ["off", "on"],
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.SWING_HORIZONTAL_MODE,
        },
    )
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    wrapper_id = _wrapper_id(hass, LIVING_KEY)
    assert wrapper_id != LIVING_ROOM
    state = hass.states.get(wrapper_id)
    assert state is not None
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_TEMPERATURE] == 21.5
    assert (
        state.attributes[ATTR_SUPPORTED_FEATURES]
        == ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.SWING_HORIZONTAL_MODE
    )

    hass.states.async_set(
        LIVING_ROOM,
        HVACMode.COOL,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.COOL],
            ATTR_TEMPERATURE: 19,
            ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.TARGET_TEMPERATURE,
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get(wrapper_id)
    assert state is not None
    assert state.state == HVACMode.COOL
    assert state.attributes[ATTR_TEMPERATURE] == 19

    hass.states.async_set(LIVING_ROOM, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    state = hass.states.get(wrapper_id)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


async def test_one_wrapper_entity_per_target(hass: HomeAssistant) -> None:
    """Test a multi-target room exposes one wrapper per target on one device."""
    set_target_state(hass, LIVING_ROOM)
    set_target_state(hass, BEDROOM)
    entry = make_room_entry(
        title="Home",
        targets=[
            make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY),
            make_target(BEDROOM, "Bedroom", key=BEDROOM_KEY),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    living = registry.async_get(_wrapper_id(hass, LIVING_KEY))
    bedroom = registry.async_get(_wrapper_id(hass, BEDROOM_KEY))
    assert living is not None and bedroom is not None
    assert living.unique_id == LIVING_KEY
    assert bedroom.unique_id == BEDROOM_KEY
    assert living.entity_id != bedroom.entity_id

    # Both wrappers advertise the whole room once every entity is registered.
    living_state = hass.states.get(living.entity_id)
    assert living_state is not None
    assert set(living_state.attributes[ATTR_ROOM_ENTITIES]) == {
        living.entity_id,
        bedroom.entity_id,
    }


async def test_exposes_new_plan_and_override_attributes(hass: HomeAssistant) -> None:
    """Test the wrapper advertises the plan and hold diagnostics."""
    await _setup_schedule_helper(hass)
    set_target_state(hass, LIVING_ROOM)
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)],
        behaviors={
            LIVING_KEY: TargetBehavior(schedule_enabled=True, apply_on_start=False)
        },
        plans=[
            PlanConfig(
                id="plan-default",
                name="Default",
                schedules={LIVING_KEY: "schedule.office"},
            )
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    wrapper_id = _wrapper_id(hass, LIVING_KEY)
    attrs = hass.states.get(wrapper_id).attributes

    # New room and plan attributes.
    assert attrs[ATTR_TARGET_KEY] == LIVING_KEY
    assert attrs[ATTR_ROOM_ENTITIES] == [wrapper_id]
    assert attrs[ATTR_PLAN_OPTIONS] == ["Default"]
    assert isinstance(attrs[ATTR_PLAN_SCHEDULES], dict)
    assert "Default" in attrs[ATTR_PLAN_SCHEDULES]
    assert attrs[ATTR_ACTIVE_PLAN] == "Default"
    assert attrs[ATTR_PLAN_SELECTION_MODE] == PLAN_MODE_MANUAL
    assert attrs[ATTR_PLAN_RESOLVED_AUTOMATICALLY] is False
    assert attrs[ATTR_OVERRIDE_ACTIVE] is False
    assert attrs[ATTR_OVERRIDE_UNTIL] is None
    assert attrs[ATTR_OVERRIDE_BLOCK] is None

    # The pre-room attributes still describe the active plan's helper.
    assert attrs[ATTR_SCHEDULE_ENABLED] is True
    assert attrs[ATTR_SCHEDULE_ENTITY_ID] == "schedule.office"
    assert attrs[ATTR_SCHEDULE_ID] == "office"
    assert attrs[ATTR_SCHEDULE_ACTIVE] is False
    assert attrs[ATTR_ACTIVE_SCHEDULE_BLOCK] is None
    # A real schedule helper reports its next boundary as an ISO timestamp.
    assert isinstance(attrs[ATTR_NEXT_SCHEDULE_EVENT], str)
    assert attrs[ATTR_SCHEDULE_ISSUES] == []
    assert attrs[ATTR_LEGACY_SCHEDULE] is None
    assert attrs[ATTR_TIMER_ACTION] is None
    assert attrs[ATTR_TIMER_DEADLINE] is None


async def test_enable_and_disable_schedule_scoped_to_one_target(
    hass: HomeAssistant,
) -> None:
    """Test enabling and disabling only touches the aimed-at target."""
    await _setup_schedule_helper(hass)
    set_target_state(hass, LIVING_ROOM)
    set_target_state(hass, BEDROOM)
    entry = make_room_entry(
        title="Home",
        targets=[
            make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY),
            make_target(BEDROOM, "Bedroom", key=BEDROOM_KEY),
        ],
        behaviors={
            LIVING_KEY: TargetBehavior(schedule_enabled=False),
            BEDROOM_KEY: TargetBehavior(schedule_enabled=False),
        },
        plans=[
            PlanConfig(
                id="plan-default",
                name="Default",
                schedules={LIVING_KEY: "schedule.office"},
            )
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ENABLE_SCHEDULE,
        {ATTR_ENTITY_ID: _wrapper_id(hass, LIVING_KEY)},
        blocking=True,
    )
    await hass.async_block_till_done()

    room = RoomConfig.from_entry(entry)
    assert room.behavior_for(LIVING_KEY).schedule_enabled is True
    assert room.behavior_for(BEDROOM_KEY).schedule_enabled is False

    await hass.services.async_call(
        DOMAIN,
        SERVICE_DISABLE_SCHEDULE,
        {ATTR_ENTITY_ID: _wrapper_id(hass, LIVING_KEY)},
        blocking=True,
    )
    await hass.async_block_till_done()

    room = RoomConfig.from_entry(entry)
    assert room.behavior_for(LIVING_KEY).schedule_enabled is False
    assert room.behavior_for(BEDROOM_KEY).schedule_enabled is False


async def test_enable_schedule_rejects_when_no_schedule_linked(
    hass: HomeAssistant,
) -> None:
    """Test enabling the schedule is rejected when no helper is linked."""
    set_target_state(hass, LIVING_ROOM)
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError, match="no schedule helper is linked"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ENABLE_SCHEDULE,
            {ATTR_ENTITY_ID: _wrapper_id(hass, LIVING_KEY)},
            blocking=True,
        )


async def test_link_schedule_without_plan_uses_active_plan(
    hass: HomeAssistant,
) -> None:
    """Test linking with no plan targets the active plan for this target."""
    await _setup_schedule_helper(hass)
    set_target_state(hass, LIVING_ROOM)
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)],
        plans=[PlanConfig(id="plan-default", name="Default")],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_LINK_SCHEDULE,
        {ATTR_ENTITY_ID: _wrapper_id(hass, LIVING_KEY), ATTR_SCHEDULE_ID: "office"},
        blocking=True,
    )
    await hass.async_block_till_done()

    room = RoomConfig.from_entry(entry)
    assert room.plan_by_name("Default").schedule_for(LIVING_KEY) == "schedule.office"
    assert room.behavior_for(LIVING_KEY).schedule_enabled is True


async def test_link_schedule_with_named_plan(hass: HomeAssistant) -> None:
    """Test linking a schedule helper into a specific named plan."""
    await _setup_schedule_helper(hass)
    set_target_state(hass, LIVING_ROOM)
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)],
        plans=[
            PlanConfig(id="plan-default", name="Default"),
            PlanConfig(id="plan-night", name="Night"),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_LINK_SCHEDULE,
        {
            ATTR_ENTITY_ID: _wrapper_id(hass, LIVING_KEY),
            ATTR_SCHEDULE_ID: "office",
            ATTR_PLAN: "Night",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    room = RoomConfig.from_entry(entry)
    assert room.plan_by_name("Night").schedule_for(LIVING_KEY) == "schedule.office"
    # The Default plan is untouched.
    assert room.plan_by_name("Default").schedule_for(LIVING_KEY) is None


async def test_set_and_clear_override(hass: HomeAssistant) -> None:
    """Test setting and clearing a temporary hold through services."""
    set_target_state(hass, LIVING_ROOM)
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    wrapper_id = _wrapper_id(hass, LIVING_KEY)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_OVERRIDE,
        {
            ATTR_ENTITY_ID: wrapper_id,
            ATTR_UNTIL_NEXT_BLOCK: True,
            "hvac_mode": HVACMode.HEAT,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    attrs = hass.states.get(wrapper_id).attributes
    assert attrs[ATTR_OVERRIDE_ACTIVE] is True
    assert attrs[ATTR_OVERRIDE_UNTIL] is not None
    assert attrs[ATTR_OVERRIDE_BLOCK]["hvac_mode"] == HVACMode.HEAT

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CLEAR_OVERRIDE,
        {ATTR_ENTITY_ID: wrapper_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    attrs = hass.states.get(wrapper_id).attributes
    assert attrs[ATTR_OVERRIDE_ACTIVE] is False
    assert attrs[ATTR_OVERRIDE_UNTIL] is None
    assert attrs[ATTR_OVERRIDE_BLOCK] is None


async def test_set_override_rejects_empty_hold(hass: HomeAssistant) -> None:
    """Test a hold with no climate settings is rejected."""
    set_target_state(hass, LIVING_ROOM)
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError, match="at least one climate setting"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_OVERRIDE,
            {ATTR_ENTITY_ID: _wrapper_id(hass, LIVING_KEY)},
            blocking=True,
        )


async def test_select_plan_switches_active_plan(hass: HomeAssistant) -> None:
    """Test selecting a plan by name changes the whole room's active plan."""
    set_target_state(hass, LIVING_ROOM)
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)],
        plans=[
            PlanConfig(id="plan-default", name="Default"),
            PlanConfig(id="plan-night", name="Night"),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    wrapper_id = _wrapper_id(hass, LIVING_KEY)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SELECT_PLAN,
        {ATTR_ENTITY_ID: wrapper_id, ATTR_PLAN: "Night"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(wrapper_id).attributes[ATTR_ACTIVE_PLAN] == "Night"


async def test_select_plan_rejects_unknown_plan(hass: HomeAssistant) -> None:
    """Test selecting a plan that does not exist is rejected."""
    set_target_state(hass, LIVING_ROOM)
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SELECT_PLAN,
            {ATTR_ENTITY_ID: _wrapper_id(hass, LIVING_KEY), ATTR_PLAN: "Nope"},
            blocking=True,
        )


async def test_timer_services_update_wrapper_state(hass: HomeAssistant) -> None:
    """Test starting, replacing, and cancelling timers through services."""
    set_target_state(hass, LIVING_ROOM, hvac_modes=[HVACMode.OFF, HVACMode.HEAT])
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    wrapper_id = _wrapper_id(hass, LIVING_KEY)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_START_ON_TIMER,
        {ATTR_ENTITY_ID: wrapper_id, ATTR_DURATION: timedelta(minutes=30)},
        blocking=True,
    )
    state = hass.states.get(wrapper_id)
    assert state.attributes[ATTR_TIMER_ACTION] == "on"
    assert state.attributes[ATTR_TIMER_DEADLINE] is not None

    await hass.services.async_call(
        DOMAIN,
        SERVICE_START_OFF_TIMER,
        {ATTR_ENTITY_ID: wrapper_id, ATTR_DURATION: timedelta(hours=1)},
        blocking=True,
    )
    assert hass.states.get(wrapper_id).attributes[ATTR_TIMER_ACTION] == "off"

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CANCEL_TIMER,
        {ATTR_ENTITY_ID: wrapper_id},
        blocking=True,
    )
    state = hass.states.get(wrapper_id)
    assert state.attributes[ATTR_TIMER_ACTION] is None
    assert state.attributes[ATTR_TIMER_DEADLINE] is None


async def test_timer_service_rejects_zero_duration(hass: HomeAssistant) -> None:
    """Test timer duration validation occurs at the service boundary."""
    set_target_state(hass, LIVING_ROOM)
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_ON_TIMER,
            {
                ATTR_ENTITY_ID: _wrapper_id(hass, LIVING_KEY),
                ATTR_DURATION: timedelta(0),
            },
            blocking=True,
        )


async def test_temperature_service_end_to_end(hass: HomeAssistant) -> None:
    """Test set temperature routes from the wrapper to its target once."""
    assert await async_setup_component(hass, CLIMATE_DOMAIN, {})
    target = _TargetClimate()
    await hass.data[DATA_COMPONENT].async_add_entities([target])
    assert target.entity_id == LIVING_ROOM

    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: _wrapper_id(hass, LIVING_KEY), ATTR_TEMPERATURE: 23},
        blocking=True,
    )

    assert target.temperature_calls == [
        {ATTR_ENTITY_ID: [LIVING_ROOM], ATTR_TEMPERATURE: 23.0}
    ]


async def test_forwards_climate_services_to_target(hass: HomeAssistant) -> None:
    """Test forwarding service data to the wrapped target entity."""
    set_target_state(hass, LIVING_ROOM)
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    entity = ScheduledClimateEntity(
        entry, coordinator, coordinator.controller_for(LIVING_KEY)
    )
    entity.hass = hass
    entity.entity_id = "climate.living_room_scheduled"

    calls: list[ServiceCall] = []

    async def capture_call(call: ServiceCall) -> None:
        calls.append(call)

    hass.services.async_register(CLIMATE_DOMAIN, SERVICE_SET_TEMPERATURE, capture_call)
    hass.services.async_register(
        CLIMATE_DOMAIN, SERVICE_SET_SWING_HORIZONTAL_MODE, capture_call
    )

    await entity.async_set_temperature(**{ATTR_TEMPERATURE: 23})
    await entity.async_set_swing_horizontal_mode("off")

    assert calls[0].data == {ATTR_ENTITY_ID: LIVING_ROOM, ATTR_TEMPERATURE: 23}
    assert calls[1].data == {
        ATTR_ENTITY_ID: LIVING_ROOM,
        ATTR_SWING_HORIZONTAL_MODE: "off",
    }


async def test_rejects_forwarding_to_itself(hass: HomeAssistant) -> None:
    """Test a wrapper cannot recursively forward services to itself."""
    set_target_state(hass, LIVING_ROOM)
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    entity = ScheduledClimateEntity(
        entry, coordinator, coordinator.controller_for(LIVING_KEY)
    )
    entity.hass = hass
    entity.entity_id = LIVING_ROOM

    with pytest.raises(
        ServiceValidationError, match="cannot use itself as its target entity"
    ):
        await entity.async_set_temperature(**{ATTR_TEMPERATURE: 23})


async def test_migrates_wrapper_entity_id_matching_target(
    hass: HomeAssistant,
) -> None:
    """Test a legacy wrapper ID matching its target is renamed on setup."""
    entry = make_room_entry(
        targets=[make_target(LIVING_ROOM, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    legacy_wrapper = registry.async_get_or_create(
        CLIMATE_DOMAIN,
        DOMAIN,
        LIVING_KEY,
        suggested_object_id="living_room",
        config_entry=entry,
    )
    assert legacy_wrapper.entity_id == LIVING_ROOM
    set_target_state(hass, LIVING_ROOM)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert (
        registry.async_get_entity_id(CLIMATE_DOMAIN, DOMAIN, LIVING_KEY)
        == "climate.living_room_scheduled"
    )


async def test_follows_target_entity_rename(hass: HomeAssistant) -> None:
    """Test persisting and following a target entity ID change."""
    registry = er.async_get(hass)
    target = registry.async_get_or_create(
        CLIMATE_DOMAIN, "test", "target", suggested_object_id="living_room"
    )
    set_target_state(hass, target.entity_id, hvac_modes=[HVACMode.OFF, HVACMode.HEAT])
    entry = make_room_entry(
        targets=[make_target(target.entity_id, "Living Room", key=LIVING_KEY)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    new_target = "climate.family_room"
    registry.async_update_entity(target.entity_id, new_entity_id=new_target)
    set_target_state(
        hass, new_target, HVACMode.COOL, hvac_modes=[HVACMode.OFF, HVACMode.COOL]
    )
    await hass.async_block_till_done()

    room = RoomConfig.from_entry(entry)
    assert room.target_by_key(LIVING_KEY).entity_id == new_target
    state = hass.states.get(_wrapper_id(hass, LIVING_KEY))
    assert state is not None
    assert state.state == HVACMode.COOL
