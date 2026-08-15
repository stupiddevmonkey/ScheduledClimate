"""Tests for the Scheduled Climate wrapper entity."""

from datetime import timedelta

import pytest
import voluptuous as vol
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
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scheduled_climate.climate import ScheduledClimateEntity
from custom_components.scheduled_climate.const import (
    ATTR_ACTIVE_SCHEDULE_BLOCK,
    ATTR_DURATION,
    ATTR_NEXT_SCHEDULE_EVENT,
    ATTR_SCHEDULE_ACTIVE,
    ATTR_SCHEDULE_ENABLED,
    ATTR_SCHEDULE_ENTITY_ID,
    ATTR_SCHEDULE_ID,
    ATTR_SCHEDULE_ISSUES,
    ATTR_TEMPERATURE_UNIT,
    ATTR_TIMER_ACTION,
    ATTR_TIMER_DEADLINE,
    CONF_APPLY_ON_START,
    CONF_SCHEDULE_ENABLED,
    CONF_SCHEDULE_ENTITY_ID,
    CONF_TARGET_ENTITY_ID,
    DOMAIN,
    SERVICE_CANCEL_TIMER,
    SERVICE_DISABLE_SCHEDULE,
    SERVICE_ENABLE_SCHEDULE,
    SERVICE_LINK_SCHEDULE,
    SERVICE_START_OFF_TIMER,
    SERVICE_START_ON_TIMER,
)
from custom_components.scheduled_climate.schedule import ScheduleManager

TARGET_ENTITY_ID = "climate.living_room"


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


async def test_mirrors_state_and_forwards_temperature(hass: HomeAssistant) -> None:
    """Test target state mirroring and temperature forwarding."""
    hass.states.async_set(
        TARGET_ENTITY_ID,
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
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID, "name": "Living Room"},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    wrapper = next(
        entity
        for entity in registry.entities.values()
        if entity.config_entry_id == entry.entry_id
    )
    assert wrapper.entity_id != TARGET_ENTITY_ID
    state = hass.states.get(wrapper.entity_id)
    assert state is not None
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_TEMPERATURE] == 21.5
    assert state.attributes[ATTR_SCHEDULE_ENABLED] is False
    assert state.attributes[ATTR_SCHEDULE_ENTITY_ID] is None
    assert state.attributes[ATTR_SCHEDULE_ID] is None
    assert state.attributes[ATTR_SCHEDULE_ACTIVE] is False
    assert state.attributes[ATTR_ACTIVE_SCHEDULE_BLOCK] is None
    assert state.attributes[ATTR_NEXT_SCHEDULE_EVENT] is None
    assert state.attributes[ATTR_SCHEDULE_ISSUES] == []
    assert state.attributes[ATTR_TIMER_ACTION] is None
    assert state.attributes[ATTR_TIMER_DEADLINE] is None
    assert (
        state.attributes[ATTR_SUPPORTED_FEATURES]
        == ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.SWING_HORIZONTAL_MODE
    )

    hass.states.async_set(
        TARGET_ENTITY_ID,
        HVACMode.COOL,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.COOL],
            ATTR_TEMPERATURE: 19,
            ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.TARGET_TEMPERATURE,
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get(wrapper.entity_id)
    assert state is not None
    assert state.state == HVACMode.COOL
    assert state.attributes[ATTR_TEMPERATURE] == 19

    hass.states.async_set(TARGET_ENTITY_ID, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    state = hass.states.get(wrapper.entity_id)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


async def test_migrates_wrapper_entity_id_matching_target(
    hass: HomeAssistant,
) -> None:
    """Test a legacy wrapper ID matching its target is migrated on setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID, "name": "Living Room"},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    legacy_wrapper = registry.async_get_or_create(
        CLIMATE_DOMAIN,
        DOMAIN,
        entry.entry_id,
        suggested_object_id="living_room",
        config_entry=entry,
    )
    assert legacy_wrapper.entity_id == TARGET_ENTITY_ID
    hass.states.async_set(
        TARGET_ENTITY_ID,
        HVACMode.HEAT,
        {ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS},
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert (
        registry.async_get_entity_id(CLIMATE_DOMAIN, DOMAIN, entry.entry_id)
        == "climate.living_room_scheduled"
    )


async def test_timer_services_update_wrapper_state(hass: HomeAssistant) -> None:
    """Test starting, replacing, and cancelling timers through services."""
    hass.states.async_set(
        TARGET_ENTITY_ID,
        HVACMode.HEAT,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT],
            ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID, "name": "Living Room"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    wrapper = next(
        entity
        for entity in registry.entities.values()
        if entity.config_entry_id == entry.entry_id
    )
    await hass.services.async_call(
        DOMAIN,
        SERVICE_START_ON_TIMER,
        {
            ATTR_ENTITY_ID: wrapper.entity_id,
            ATTR_DURATION: timedelta(minutes=30),
        },
        blocking=True,
    )

    state = hass.states.get(wrapper.entity_id)
    assert state is not None
    assert state.attributes[ATTR_TIMER_ACTION] == "on"
    assert state.attributes[ATTR_TIMER_DEADLINE] is not None

    await hass.services.async_call(
        DOMAIN,
        SERVICE_START_OFF_TIMER,
        {
            ATTR_ENTITY_ID: wrapper.entity_id,
            ATTR_DURATION: timedelta(hours=1),
        },
        blocking=True,
    )
    state = hass.states.get(wrapper.entity_id)
    assert state is not None
    assert state.attributes[ATTR_TIMER_ACTION] == "off"

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CANCEL_TIMER,
        {ATTR_ENTITY_ID: wrapper.entity_id},
        blocking=True,
    )
    state = hass.states.get(wrapper.entity_id)
    assert state is not None
    assert state.attributes[ATTR_TIMER_ACTION] is None
    assert state.attributes[ATTR_TIMER_DEADLINE] is None


async def test_timer_service_rejects_zero_duration(hass: HomeAssistant) -> None:
    """Test timer duration validation occurs at the service boundary."""
    hass.states.async_set(
        TARGET_ENTITY_ID,
        HVACMode.HEAT,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT],
            ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID, "name": "Living Room"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    wrapper = next(
        entity
        for entity in er.async_get(hass).entities.values()
        if entity.config_entry_id == entry.entry_id
    )

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_ON_TIMER,
            {
                ATTR_ENTITY_ID: wrapper.entity_id,
                ATTR_DURATION: timedelta(0),
            },
            blocking=True,
        )


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


async def _setup_wrapper(hass: HomeAssistant, options: dict[str, object]) -> str:
    """Set up a wrapper entry and return its entity id."""
    hass.states.async_set(
        TARGET_ENTITY_ID,
        HVACMode.HEAT,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT],
            ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title="Living Room",
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID, "name": "Living Room"},
        options={CONF_APPLY_ON_START: False, **options},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return next(
        entity.entity_id
        for entity in er.async_get(hass).entities.values()
        if entity.config_entry_id == entry.entry_id
    )


async def test_link_schedule_service_links_helper(hass: HomeAssistant) -> None:
    """Test linking a schedule helper through the wrapper service."""
    await _setup_schedule_helper(hass)
    wrapper_entity_id = await _setup_wrapper(hass, {})
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_LINK_SCHEDULE,
        {ATTR_ENTITY_ID: wrapper_entity_id, ATTR_SCHEDULE_ID: "office"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.options[CONF_SCHEDULE_ENTITY_ID] == "schedule.office"
    assert entry.options[CONF_SCHEDULE_ENABLED] is True

    state = hass.states.get(wrapper_entity_id)
    assert state is not None
    assert state.attributes[ATTR_SCHEDULE_ENTITY_ID] == "schedule.office"
    assert state.attributes[ATTR_SCHEDULE_ID] == "office"
    assert state.attributes[ATTR_SCHEDULE_ENABLED] is True


async def test_link_schedule_service_unlinks_helper(hass: HomeAssistant) -> None:
    """Test unlinking the schedule helper disables scheduling."""
    await _setup_schedule_helper(hass)
    wrapper_entity_id = await _setup_wrapper(
        hass,
        {
            CONF_SCHEDULE_ENTITY_ID: "schedule.office",
            CONF_SCHEDULE_ENABLED: True,
        },
    )
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_LINK_SCHEDULE,
        {ATTR_ENTITY_ID: wrapper_entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert CONF_SCHEDULE_ENTITY_ID not in entry.options
    assert entry.options[CONF_SCHEDULE_ENABLED] is False

    manager: ScheduleManager = hass.data[DOMAIN][entry.entry_id]
    assert manager.enabled is False
    assert manager.schedule_entity_id is None


async def test_link_schedule_rejects_unknown_schedule(hass: HomeAssistant) -> None:
    """Test linking an unknown schedule helper is rejected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID},
    )
    entry.add_to_hass(hass)
    entity = ScheduledClimateEntity(
        entry.entry_id,
        "Living Room",
        TARGET_ENTITY_ID,
        ScheduleManager(hass, entry),
    )
    entity.hass = hass

    with pytest.raises(ServiceValidationError):
        await entity.async_link_schedule("missing")

    assert entry.options == {}


async def test_enable_schedule_service(hass: HomeAssistant) -> None:
    """Test enabling the schedule updates the option and applies the active block."""
    await _setup_schedule_helper(hass)
    wrapper_entity_id = await _setup_wrapper(
        hass,
        {
            CONF_SCHEDULE_ENTITY_ID: "schedule.office",
            CONF_SCHEDULE_ENABLED: False,
        },
    )
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ENABLE_SCHEDULE,
        {ATTR_ENTITY_ID: wrapper_entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.options[CONF_SCHEDULE_ENABLED] is True
    state = hass.states.get(wrapper_entity_id)
    assert state is not None
    assert state.attributes[ATTR_SCHEDULE_ENABLED] is True


async def test_disable_schedule_service(hass: HomeAssistant) -> None:
    """Test disabling the schedule keeps the helper linked but pauses application."""
    await _setup_schedule_helper(hass)
    wrapper_entity_id = await _setup_wrapper(
        hass,
        {
            CONF_SCHEDULE_ENTITY_ID: "schedule.office",
            CONF_SCHEDULE_ENABLED: True,
        },
    )
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    await hass.services.async_call(
        DOMAIN,
        SERVICE_DISABLE_SCHEDULE,
        {ATTR_ENTITY_ID: wrapper_entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.options[CONF_SCHEDULE_ENABLED] is False
    assert entry.options[CONF_SCHEDULE_ENTITY_ID] == "schedule.office"
    state = hass.states.get(wrapper_entity_id)
    assert state is not None
    assert state.attributes[ATTR_SCHEDULE_ENABLED] is False
    assert state.attributes[ATTR_SCHEDULE_ENTITY_ID] == "schedule.office"


async def test_enable_schedule_rejects_when_no_schedule_linked(
    hass: HomeAssistant,
) -> None:
    """Test enabling the schedule is rejected when no helper is linked."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID},
    )
    entry.add_to_hass(hass)
    entity = ScheduledClimateEntity(
        entry.entry_id,
        "Living Room",
        TARGET_ENTITY_ID,
        ScheduleManager(hass, entry),
    )
    entity.hass = hass

    with pytest.raises(ServiceValidationError, match="no schedule helper is linked"):
        await entity.async_enable_schedule()

    assert entry.options == {}


async def test_forwards_climate_services(hass: HomeAssistant) -> None:
    """Test forwarding service data to the target entity."""
    calls: list[ServiceCall] = []

    async def capture_call(call: ServiceCall) -> None:
        calls.append(call)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID},
    )
    entity = ScheduledClimateEntity(
        "entry",
        "Living Room",
        TARGET_ENTITY_ID,
        ScheduleManager(hass, entry),
    )
    entity.hass = hass
    hass.services.async_register(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        capture_call,
    )
    hass.services.async_register(
        CLIMATE_DOMAIN,
        SERVICE_SET_SWING_HORIZONTAL_MODE,
        capture_call,
    )

    await entity.async_set_temperature(**{ATTR_TEMPERATURE: 23})
    await entity.async_set_swing_horizontal_mode("off")

    assert calls[0].data == {
        ATTR_ENTITY_ID: TARGET_ENTITY_ID,
        ATTR_TEMPERATURE: 23,
    }
    assert calls[1].data == {
        ATTR_ENTITY_ID: TARGET_ENTITY_ID,
        ATTR_SWING_HORIZONTAL_MODE: "off",
    }


async def test_temperature_service_end_to_end(hass: HomeAssistant) -> None:
    """Test set temperature routes from the wrapper to its target once."""
    assert await async_setup_component(hass, CLIMATE_DOMAIN, {})
    target = _TargetClimate()
    await hass.data[DATA_COMPONENT].async_add_entities([target])
    assert target.entity_id == TARGET_ENTITY_ID

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Room Schedule",
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID, "name": "Living Room"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    wrapper = next(
        entity
        for entity in er.async_get(hass).entities.values()
        if entity.config_entry_id == entry.entry_id
    )

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: wrapper.entity_id,
            ATTR_TEMPERATURE: 23,
        },
        blocking=True,
    )

    assert target.temperature_calls == [
        {
            ATTR_ENTITY_ID: [TARGET_ENTITY_ID],
            ATTR_TEMPERATURE: 23.0,
        }
    ]


async def test_rejects_forwarding_to_itself(hass: HomeAssistant) -> None:
    """Test a malformed self-target does not recursively forward services."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID},
    )
    entity = ScheduledClimateEntity(
        "entry",
        "Living Room",
        TARGET_ENTITY_ID,
        ScheduleManager(hass, entry),
    )
    entity.hass = hass
    entity.entity_id = TARGET_ENTITY_ID

    with pytest.raises(
        ServiceValidationError,
        match="cannot use itself as its target entity",
    ):
        await entity.async_set_temperature(**{ATTR_TEMPERATURE: 23})


async def test_follows_target_entity_rename(hass: HomeAssistant) -> None:
    """Test persisting and following a target entity ID change."""
    registry = er.async_get(hass)
    target = registry.async_get_or_create(
        CLIMATE_DOMAIN,
        "test",
        "target",
        suggested_object_id="living_room",
    )
    hass.states.async_set(
        target.entity_id,
        HVACMode.HEAT,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT],
            ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        data={CONF_TARGET_ENTITY_ID: target.entity_id, "name": "Living Room"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    new_target = "climate.family_room"
    registry.async_update_entity(target.entity_id, new_entity_id=new_target)
    hass.states.async_set(
        new_target,
        HVACMode.COOL,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.COOL],
            ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
        },
    )
    await hass.async_block_till_done()

    assert entry.data[CONF_TARGET_ENTITY_ID] == new_target
    wrapper = next(
        entity
        for entity in registry.entities.values()
        if entity.config_entry_id == entry.entry_id
    )
    state = hass.states.get(wrapper.entity_id)
    assert state is not None
    assert state.state == HVACMode.COOL

    final_target = "climate.downstairs"
    registry.async_update_entity(new_target, new_entity_id=final_target)
    hass.states.async_set(
        final_target,
        HVACMode.HEAT,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT],
            ATTR_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
        },
    )
    await hass.async_block_till_done()

    assert entry.data[CONF_TARGET_ENTITY_ID] == final_target
    state = hass.states.get(wrapper.entity_id)
    assert state is not None
    assert state.state == HVACMode.HEAT
