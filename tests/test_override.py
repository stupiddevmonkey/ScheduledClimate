"""Tests for temporary holds."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from homeassistant.components.climate import (
    ATTR_FAN_MODES,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_TEMPERATURE,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.schedule import ATTR_NEXT_EVENT
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.scheduled_climate.const import (
    ATTR_DURATION,
    ATTR_OVERRIDE_ACTIVE,
    ATTR_OVERRIDE_BLOCK,
    ATTR_OVERRIDE_UNTIL,
    ATTR_UNTIL_NEXT_BLOCK,
    DOMAIN,
    SERVICE_CLEAR_OVERRIDE,
    SERVICE_SET_OVERRIDE,
    SERVICE_START_OFF_TIMER,
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
SCHEDULE_ENTITY_ID = "schedule.living_room"
TARGET_KEY = "target-1"
TARGET_FEATURES = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.TARGET_HUMIDITY
    | ClimateEntityFeature.FAN_MODE
)


def _set_target(hass: HomeAssistant, state: str = HVACMode.HEAT) -> None:
    """Publish the wrapped climate target state."""
    hass.states.async_set(
        TARGET_ENTITY_ID,
        state,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL],
            ATTR_FAN_MODES: ["low", "high"],
            ATTR_SUPPORTED_FEATURES: TARGET_FEATURES,
        },
    )


def _set_schedule(hass: HomeAssistant, state: str, **data: Any) -> None:
    """Publish the linked schedule helper state."""
    hass.states.async_set(SCHEDULE_ENTITY_ID, state, data)


def _capture_climate_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Record every climate service call in order."""
    calls: list[ServiceCall] = []

    async def handler(call: ServiceCall) -> None:
        calls.append(call)

    for service in (
        SERVICE_SET_HVAC_MODE,
        SERVICE_SET_TEMPERATURE,
        SERVICE_SET_FAN_MODE,
        SERVICE_SET_HUMIDITY,
    ):
        hass.services.async_register(CLIMATE_DOMAIN, service, handler)
    return calls


async def _setup_room(
    hass: HomeAssistant,
    *,
    override: OverrideConfig | None = None,
    apply_on_start: bool = False,
) -> tuple[MockConfigEntry, str]:
    """Set up a one-target room following a schedule helper."""
    target = TargetConfig(
        key=TARGET_KEY, entity_id=TARGET_ENTITY_ID, name="Living Room"
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        version=3,
        data={"name": "Living Room", "targets": targets_as_data([target])},
        options=build_options(
            behaviors={
                TARGET_KEY: TargetBehavior(
                    schedule_enabled=True, apply_on_start=apply_on_start
                )
            },
            plans=[
                PlanConfig(
                    id="default",
                    name="Default",
                    schedules={TARGET_KEY: SCHEDULE_ENTITY_ID},
                )
            ],
            plan_selection=PlanSelectionConfig(),
            override=override or OverrideConfig(),
        ),
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    wrapper_entity_id = er.async_get(hass).async_get_entity_id(
        CLIMATE_DOMAIN, DOMAIN, TARGET_KEY
    )
    assert wrapper_entity_id is not None
    return entry, wrapper_entity_id


async def _call(hass: HomeAssistant, service: str, entity_id: str, **data: Any) -> None:
    """Call one Scheduled Climate entity service."""
    await hass.services.async_call(
        DOMAIN, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )
    await hass.async_block_till_done()


async def test_hold_applies_and_suppresses_the_schedule(
    hass: HomeAssistant,
) -> None:
    """A hold pushes its own settings and blocks schedule changes."""
    _set_target(hass)
    _set_schedule(hass, STATE_ON, temperature=18)
    _entry, wrapper = await _setup_room(hass)
    calls = _capture_climate_calls(hass)

    await _call(hass, SERVICE_SET_OVERRIDE, wrapper, temperature=23, fan_mode="high")

    assert [call.service for call in calls] == [
        SERVICE_SET_TEMPERATURE,
        SERVICE_SET_FAN_MODE,
    ]
    assert calls[0].data[ATTR_TEMPERATURE] == 23

    state = hass.states.get(wrapper)
    assert state.attributes[ATTR_OVERRIDE_ACTIVE] is True
    assert state.attributes[ATTR_OVERRIDE_UNTIL] is not None
    assert state.attributes[ATTR_OVERRIDE_BLOCK][ATTR_TEMPERATURE] == 23

    calls.clear()
    _set_schedule(hass, STATE_ON, temperature=15)
    await hass.async_block_till_done()
    assert calls == []


async def test_clearing_a_hold_resumes_the_schedule(hass: HomeAssistant) -> None:
    """Ending a hold immediately re-applies the active block."""
    _set_target(hass)
    _set_schedule(hass, STATE_ON, temperature=18)
    _entry, wrapper = await _setup_room(hass)

    await _call(hass, SERVICE_SET_OVERRIDE, wrapper, temperature=23)
    calls = _capture_climate_calls(hass)

    _set_schedule(hass, STATE_ON, temperature=15)
    await hass.async_block_till_done()
    assert calls == []

    await _call(hass, SERVICE_CLEAR_OVERRIDE, wrapper)

    assert any(
        call.service == SERVICE_SET_TEMPERATURE and call.data[ATTR_TEMPERATURE] == 15
        for call in calls
    )
    assert hass.states.get(wrapper).attributes[ATTR_OVERRIDE_ACTIVE] is False


async def test_hold_expiry_returns_control_to_the_schedule(
    hass: HomeAssistant,
) -> None:
    """When a hold lapses the current block is applied again."""
    _set_target(hass)
    _set_schedule(hass, STATE_ON, temperature=18)
    _entry, wrapper = await _setup_room(hass)

    await _call(
        hass,
        SERVICE_SET_OVERRIDE,
        wrapper,
        temperature=23,
        **{ATTR_DURATION: {"minutes": 30}},
    )
    calls = _capture_climate_calls(hass)

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()

    assert any(
        call.service == SERVICE_SET_TEMPERATURE and call.data[ATTR_TEMPERATURE] == 18
        for call in calls
    )
    assert hass.states.get(wrapper).attributes[ATTR_OVERRIDE_ACTIVE] is False


async def test_hold_length_is_clamped(hass: HomeAssistant) -> None:
    """A hold longer than the configured maximum is shortened."""
    _set_target(hass)
    _set_schedule(hass, STATE_OFF)
    _entry, wrapper = await _setup_room(
        hass, override=OverrideConfig(default_minutes=60, max_minutes=120)
    )

    before = dt_util.utcnow()
    await _call(
        hass,
        SERVICE_SET_OVERRIDE,
        wrapper,
        temperature=23,
        **{ATTR_DURATION: {"hours": 9}},
    )

    until = dt_util.parse_datetime(
        hass.states.get(wrapper).attributes[ATTR_OVERRIDE_UNTIL]
    )
    assert until is not None
    assert until - before <= timedelta(minutes=121)


async def test_hold_until_next_block_uses_the_helper(hass: HomeAssistant) -> None:
    """The default hold ends at the schedule helper's next boundary."""
    _set_target(hass)
    next_event = dt_util.utcnow() + timedelta(minutes=45)
    _set_schedule(hass, STATE_ON, temperature=18, **{ATTR_NEXT_EVENT: next_event})
    _entry, wrapper = await _setup_room(hass)

    await _call(
        hass,
        SERVICE_SET_OVERRIDE,
        wrapper,
        temperature=23,
        **{ATTR_UNTIL_NEXT_BLOCK: True},
    )

    until = dt_util.parse_datetime(
        hass.states.get(wrapper).attributes[ATTR_OVERRIDE_UNTIL]
    )
    assert until is not None
    assert abs((until - next_event).total_seconds()) < 2


async def test_hold_falls_back_when_no_next_block(hass: HomeAssistant) -> None:
    """Without a next boundary the default hold length is used."""
    _set_target(hass)
    _set_schedule(hass, STATE_OFF)
    _entry, wrapper = await _setup_room(
        hass, override=OverrideConfig(default_minutes=90, max_minutes=480)
    )

    before = dt_util.utcnow()
    await _call(hass, SERVICE_SET_OVERRIDE, wrapper, temperature=23)

    until = dt_util.parse_datetime(
        hass.states.get(wrapper).attributes[ATTR_OVERRIDE_UNTIL]
    )
    assert until is not None
    assert timedelta(minutes=89) <= until - before <= timedelta(minutes=91)


async def test_a_firing_timer_clears_the_hold(hass: HomeAssistant) -> None:
    """A timer is the newer intent, so it ends any running hold."""
    _set_target(hass)
    _set_schedule(hass, STATE_ON, temperature=18)
    _entry, wrapper = await _setup_room(hass)

    await _call(hass, SERVICE_SET_OVERRIDE, wrapper, temperature=23)
    assert hass.states.get(wrapper).attributes[ATTR_OVERRIDE_ACTIVE] is True

    calls = _capture_climate_calls(hass)
    await _call(
        hass, SERVICE_START_OFF_TIMER, wrapper, **{ATTR_DURATION: {"minutes": 5}}
    )
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
    await hass.async_block_till_done()

    assert hass.states.get(wrapper).attributes[ATTR_OVERRIDE_ACTIVE] is False
    assert any(
        call.service == SERVICE_SET_HVAC_MODE
        and call.data[ATTR_HVAC_MODE] == HVACMode.OFF
        for call in calls
    )


async def test_an_empty_hold_is_rejected(hass: HomeAssistant) -> None:
    """A hold that requests nothing is refused."""
    _set_target(hass)
    _set_schedule(hass, STATE_OFF)
    _entry, wrapper = await _setup_room(hass)

    with pytest.raises(ServiceValidationError):
        await _call(
            hass, SERVICE_SET_OVERRIDE, wrapper, **{ATTR_UNTIL_NEXT_BLOCK: True}
        )


async def test_expiry_reapplies_a_block_equal_to_the_pre_hold_block(
    hass: HomeAssistant,
) -> None:
    """Expiry re-applies the current block even if it never changed.

    The schedule sits on the same block throughout, so the block recorded
    while the hold ran equals the one applied before it started. The
    ``_last_applied`` sentinel must still be reset on resume, otherwise the
    target would be left stuck on the hold's settings.
    """
    _set_target(hass, HVACMode.HEAT)
    _set_schedule(hass, STATE_OFF)
    _entry, wrapper = await _setup_room(hass)
    calls = _capture_climate_calls(hass)

    # Drive the schedule to 18 so it becomes the last applied block.
    _set_schedule(hass, STATE_ON, temperature=18)
    await hass.async_block_till_done()
    assert any(
        call.service == SERVICE_SET_TEMPERATURE and call.data[ATTR_TEMPERATURE] == 18
        for call in calls
    )
    calls.clear()

    await _call(
        hass,
        SERVICE_SET_OVERRIDE,
        wrapper,
        temperature=23,
        **{ATTR_DURATION: {"minutes": 30}},
    )
    assert any(
        call.service == SERVICE_SET_TEMPERATURE and call.data[ATTR_TEMPERATURE] == 23
        for call in calls
    )
    calls.clear()

    # The schedule never moves off 18 while the hold runs.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()

    # Even though 18 equals the block applied before the hold, it is re-sent.
    assert any(
        call.service == SERVICE_SET_TEMPERATURE and call.data[ATTR_TEMPERATURE] == 18
        for call in calls
    )
    assert hass.states.get(wrapper).attributes[ATTR_OVERRIDE_ACTIVE] is False


async def test_hold_wins_over_a_block_deferred_while_unavailable(
    hass: HomeAssistant,
) -> None:
    """A hold expiring while the target is offline defers the resumed block.

    When the hold lapses the schedule block cannot be pushed to an offline
    target, so it is deferred and applied the moment the target returns.
    """
    _set_target(hass, HVACMode.HEAT)
    _set_schedule(hass, STATE_ON, temperature=21)
    entry, wrapper = await _setup_room(hass)
    calls = _capture_climate_calls(hass)
    controller = hass.data[DOMAIN][entry.entry_id].controller_for(TARGET_KEY)
    assert controller is not None

    # Hold at 23 while the target is available; it applies immediately.
    await _call(
        hass,
        SERVICE_SET_OVERRIDE,
        wrapper,
        temperature=23,
        **{ATTR_DURATION: {"minutes": 30}},
    )
    assert any(
        call.service == SERVICE_SET_TEMPERATURE and call.data[ATTR_TEMPERATURE] == 23
        for call in calls
    )
    assert controller.override.active is True

    # The target drops offline, then the hold lapses.
    _set_target(hass, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    calls.clear()

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert controller.override.active is False
    # The resumed schedule block cannot reach the offline target yet.
    assert calls == []

    # The target returns and the deferred schedule block (21) is applied.
    _set_target(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    applied = [
        call.data[ATTR_TEMPERATURE]
        for call in calls
        if call.service == SERVICE_SET_TEMPERATURE
    ]
    assert 21 in applied
