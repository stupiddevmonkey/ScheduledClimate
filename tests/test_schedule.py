"""Tests for applying the active plan's schedule helper to one target."""

from typing import Any

from conftest import make_room_entry, make_target
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
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scheduled_climate.const import (
    DOMAIN,
    ISSUE_BLOCK_UNSUPPORTED,
    ISSUE_SCHEDULE_MISSING,
    OFF_BEHAVIOR_IGNORE,
    OFF_BEHAVIOR_TURN_OFF,
)
from custom_components.scheduled_climate.models import (
    PlanConfig,
    TargetBehavior,
)
from custom_components.scheduled_climate.schedule import TargetController

TARGET_ENTITY_ID = "climate.living_room"
SCHEDULE_ENTITY_ID = "schedule.living_room"
TARGET_KEY = "living-room-key"

TARGET_FEATURES = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    | ClimateEntityFeature.FAN_MODE
    | ClimateEntityFeature.TARGET_HUMIDITY
)


def _set_target(
    hass: HomeAssistant, state: str = HVACMode.HEAT, **attributes: Any
) -> None:
    """Set the target climate entity state."""
    hass.states.async_set(
        TARGET_ENTITY_ID,
        state,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL],
            ATTR_FAN_MODES: ["low", "high"],
            ATTR_SUPPORTED_FEATURES: TARGET_FEATURES,
            **attributes,
        },
    )


def _set_schedule(hass: HomeAssistant, state: str, **data: Any) -> None:
    """Set the linked schedule helper state."""
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


async def _setup_entry(
    hass: HomeAssistant,
    *,
    schedule_enabled: bool = True,
    apply_on_start: bool = False,
    off_behavior: str = OFF_BEHAVIOR_TURN_OFF,
    default_hvac_mode: str = HVACMode.HEAT,
    schedule_entity_id: str | None = SCHEDULE_ENTITY_ID,
) -> MockConfigEntry:
    """Set up a room whose active plan links the schedule helper."""
    target = make_target(TARGET_ENTITY_ID, "Living Room", key=TARGET_KEY)
    schedules = {TARGET_KEY: schedule_entity_id} if schedule_entity_id else {}
    entry = make_room_entry(
        title="Living Room",
        targets=[target],
        behaviors={
            TARGET_KEY: TargetBehavior(
                schedule_enabled=schedule_enabled,
                default_hvac_mode=default_hvac_mode,
                off_behavior=off_behavior,
                apply_on_start=apply_on_start,
            )
        },
        plans=[PlanConfig(id="plan-default", name="Default", schedules=schedules)],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _controller(hass: HomeAssistant, entry: MockConfigEntry) -> TargetController:
    """Return the controller wrapping the single target."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    controller = coordinator.controller_for(TARGET_KEY)
    assert controller is not None
    return controller


async def test_block_applies_mode_before_setpoints(hass: HomeAssistant) -> None:
    """Test a starting block applies the HVAC mode first."""
    _set_target(hass, HVACMode.OFF)
    _set_schedule(hass, STATE_OFF)
    await _setup_entry(hass, apply_on_start=False)
    calls = _capture_climate_calls(hass)

    _set_schedule(
        hass,
        STATE_ON,
        **{
            ATTR_HVAC_MODE: HVACMode.HEAT,
            ATTR_TEMPERATURE: 21,
            ATTR_FAN_MODE: "low",
            ATTR_HUMIDITY: 45,
        },
    )
    await hass.async_block_till_done()

    assert [call.service for call in calls] == [
        SERVICE_SET_HVAC_MODE,
        SERVICE_SET_TEMPERATURE,
        SERVICE_SET_FAN_MODE,
        SERVICE_SET_HUMIDITY,
    ]
    assert calls[0].data[ATTR_HVAC_MODE] == HVACMode.HEAT
    assert calls[1].data[ATTR_TEMPERATURE] == 21
    assert calls[2].data[ATTR_FAN_MODE] == "low"
    assert calls[3].data[ATTR_HUMIDITY] == 45


async def test_next_event_change_does_not_reapply(hass: HomeAssistant) -> None:
    """Test recomputed next_event attributes do not trigger service calls."""
    _set_target(hass)
    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21, "next_event": "a"})
    await _setup_entry(hass)
    calls = _capture_climate_calls(hass)

    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21, "next_event": "b"})
    await hass.async_block_till_done()

    assert calls == []


async def test_touching_blocks_apply_new_setpoint(hass: HomeAssistant) -> None:
    """Test a data-only change while the schedule stays on is applied."""
    _set_target(hass)
    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 18})
    await _setup_entry(hass)
    calls = _capture_climate_calls(hass)

    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21})
    await hass.async_block_till_done()

    assert [call.service for call in calls] == [SERVICE_SET_TEMPERATURE]
    assert calls[0].data[ATTR_TEMPERATURE] == 21


async def test_schedule_end_turns_target_off(hass: HomeAssistant) -> None:
    """Test the target is turned off when no block is active."""
    _set_target(hass)
    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21})
    await _setup_entry(hass)
    calls = _capture_climate_calls(hass)

    _set_schedule(hass, STATE_OFF)
    await hass.async_block_till_done()

    assert [call.service for call in calls] == [SERVICE_SET_HVAC_MODE]
    assert calls[0].data[ATTR_HVAC_MODE] == HVACMode.OFF


async def test_off_behavior_ignore_leaves_target(hass: HomeAssistant) -> None:
    """Test the ignore off behavior leaves the target unchanged."""
    _set_target(hass)
    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21})
    await _setup_entry(hass, off_behavior=OFF_BEHAVIOR_IGNORE)
    calls = _capture_climate_calls(hass)

    _set_schedule(hass, STATE_OFF)
    await hass.async_block_till_done()

    assert calls == []


async def test_apply_on_start_applies_active_block(hass: HomeAssistant) -> None:
    """Test the active block is applied while setting up the entry."""
    _set_target(hass, HVACMode.OFF)
    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21})
    calls = _capture_climate_calls(hass)

    await _setup_entry(hass, apply_on_start=True)

    assert [call.service for call in calls] == [
        SERVICE_SET_HVAC_MODE,
        SERVICE_SET_TEMPERATURE,
    ]


async def test_apply_on_start_disabled_skips_active_block(
    hass: HomeAssistant,
) -> None:
    """Test the active block is not applied when startup applying is off."""
    _set_target(hass, HVACMode.OFF)
    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21})
    calls = _capture_climate_calls(hass)

    await _setup_entry(hass, apply_on_start=False)

    assert calls == []


async def test_unavailable_target_retries_when_available(
    hass: HomeAssistant,
) -> None:
    """Test a deferred block is applied once the target returns."""
    _set_target(hass, STATE_UNAVAILABLE)
    _set_schedule(hass, STATE_OFF)
    await _setup_entry(hass, apply_on_start=False)
    calls = _capture_climate_calls(hass)

    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21})
    await hass.async_block_till_done()
    assert calls == []

    _set_target(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    assert [call.service for call in calls] == [SERVICE_SET_TEMPERATURE]


async def test_restores_last_active_hvac_mode(hass: HomeAssistant) -> None:
    """Test the remembered active mode wins over the default when turning on."""
    _set_target(hass, HVACMode.HEAT)
    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21})
    # The default mode differs from the running mode so the remembered mode,
    # not the default, must be the one restored.
    await _setup_entry(hass, default_hvac_mode=HVACMode.COOL)
    calls = _capture_climate_calls(hass)

    # The schedule ends: the target is turned off and HEAT is remembered.
    _set_schedule(hass, STATE_OFF)
    await hass.async_block_till_done()
    assert [call.service for call in calls] == [SERVICE_SET_HVAC_MODE]
    assert calls[0].data[ATTR_HVAC_MODE] == HVACMode.OFF

    calls.clear()
    _set_target(hass, HVACMode.OFF)

    # A new block without a mode should turn the target back on using HEAT.
    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21})
    await hass.async_block_till_done()

    assert [call.service for call in calls] == [
        SERVICE_SET_HVAC_MODE,
        SERVICE_SET_TEMPERATURE,
    ]
    assert calls[0].data[ATTR_HVAC_MODE] == HVACMode.HEAT


async def test_unsupported_setting_records_issue(hass: HomeAssistant) -> None:
    """Test unsupported block values are reported instead of applied."""
    _set_target(hass, HVACMode.HEAT, **{ATTR_SUPPORTED_FEATURES: 0})
    _set_schedule(hass, STATE_OFF)
    entry = await _setup_entry(hass, apply_on_start=False)
    calls = _capture_climate_calls(hass)

    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21})
    await hass.async_block_till_done()

    assert calls == []
    controller = _controller(hass, entry)
    assert controller.issues

    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"{ISSUE_BLOCK_UNSUPPORTED}_{entry.entry_id}_{TARGET_KEY}"
    )
    assert issue is not None
    assert issue.translation_placeholders["name"] == "Living Room"


async def test_missing_schedule_helper_raises_issue(hass: HomeAssistant) -> None:
    """Test a linked but non-existent schedule helper raises a repair."""
    _set_target(hass)
    entry = await _setup_entry(
        hass, apply_on_start=False, schedule_entity_id="schedule.missing"
    )

    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"{ISSUE_SCHEDULE_MISSING}_{entry.entry_id}_{TARGET_KEY}"
    )
    assert issue is not None
    assert issue.translation_placeholders["name"] == "Living Room"


async def test_temperature_range_block(hass: HomeAssistant) -> None:
    """Test a block with a temperature range is applied as a range."""
    _set_target(hass)
    _set_schedule(hass, STATE_OFF)
    await _setup_entry(hass, apply_on_start=False)
    calls = _capture_climate_calls(hass)

    _set_schedule(
        hass,
        STATE_ON,
        **{ATTR_TARGET_TEMP_LOW: 18, ATTR_TARGET_TEMP_HIGH: 24},
    )
    await hass.async_block_till_done()

    assert [call.service for call in calls] == [SERVICE_SET_TEMPERATURE]
    assert calls[0].data[ATTR_TARGET_TEMP_LOW] == 18
    assert calls[0].data[ATTR_TARGET_TEMP_HIGH] == 24


async def test_disabled_schedule_is_not_applied(hass: HomeAssistant) -> None:
    """Test a linked but disabled schedule never drives the target."""
    _set_target(hass)
    _set_schedule(hass, STATE_OFF)
    await _setup_entry(hass, schedule_enabled=False)
    calls = _capture_climate_calls(hass)

    _set_schedule(hass, STATE_ON, **{ATTR_TEMPERATURE: 21})
    await hass.async_block_till_done()

    assert calls == []
