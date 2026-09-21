"""Tests for Scheduled Climate config entry migration to the room model."""

from homeassistant.components.climate import ATTR_HVAC_MODES, HVACMode
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scheduled_climate import async_migrate_entry
from custom_components.scheduled_climate.const import (
    CONF_APPLY_ON_START,
    CONF_DEFAULT_HVAC_MODE,
    CONF_LEGACY_OFF_TIME,
    CONF_LEGACY_ON_TIME,
    CONF_OFF_BEHAVIOR,
    CONF_SCHEDULE_ENABLED,
    CONF_SCHEDULE_ENTITY_ID,
    CONF_TARGET_ENTITY_ID,
    DEFAULT_APPLY_ON_START,
    DEFAULT_HVAC_MODE,
    DEFAULT_OFF_BEHAVIOR,
    DEFAULT_PLAN_NAME,
    DOMAIN,
    ISSUE_SCHEDULE_NOT_LINKED,
    OFF_BEHAVIOR_IGNORE,
)
from custom_components.scheduled_climate.models import RoomConfig

TARGET_ENTITY_ID = "climate.living_room"
SCHEDULE_ENTITY_ID = "schedule.office"


def _set_target(hass: HomeAssistant) -> None:
    """Set a usable target climate state."""
    hass.states.async_set(
        TARGET_ENTITY_ID,
        HVACMode.HEAT,
        {ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT]},
    )


async def test_migrates_version_1_to_room_model(hass: HomeAssistant) -> None:
    """Test a version 1 entry migrates all the way to the room model."""
    _set_target(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title="Living Room",
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID},
        options={
            CONF_SCHEDULE_ENABLED: True,
            "on_time": "06:30:00",
            "off_time": "22:00:00",
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 3

    room = RoomConfig.from_entry(entry)
    assert len(room.targets) == 1
    target = room.targets[0]
    # The lone target keeps the entry id as its key so the wrapper entity,
    # whose unique id is the entry id, survives the upgrade untouched.
    assert target.key == entry.entry_id
    assert target.entity_id == TARGET_ENTITY_ID

    assert room.plan_names == (DEFAULT_PLAN_NAME,)
    default_plan = room.plans[0]
    assert default_plan.schedule_for(target.key) is None

    # Version 1 has no schedule helper yet, so scheduling is off and the daily
    # times are preserved for the linked-schedule repair.
    behavior = room.behavior_for(target.key)
    assert behavior.schedule_enabled is False
    assert behavior.off_behavior == DEFAULT_OFF_BEHAVIOR
    assert behavior.apply_on_start is DEFAULT_APPLY_ON_START
    assert behavior.default_hvac_mode == DEFAULT_HVAC_MODE

    assert room.legacy_on_time == "06:30:00"
    assert room.legacy_off_time == "22:00:00"
    assert entry.options[CONF_LEGACY_ON_TIME] == "06:30:00"
    assert entry.options[CONF_LEGACY_OFF_TIME] == "22:00:00"

    # The wrapper unique id is unchanged from the pre-room scheme.
    assert (
        er.async_get(hass).async_get_entity_id(CLIMATE_DOMAIN, DOMAIN, entry.entry_id)
        is not None
    )

    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"{ISSUE_SCHEDULE_NOT_LINKED}_{entry.entry_id}_{target.key}"
    )
    assert issue is not None


async def test_migrates_version_2_with_linked_schedule(hass: HomeAssistant) -> None:
    """Test a linked v2 schedule and behaviour flags land in the Default plan."""
    _set_target(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title="Living Room",
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID},
        options={
            CONF_SCHEDULE_ENABLED: True,
            CONF_SCHEDULE_ENTITY_ID: SCHEDULE_ENTITY_ID,
            CONF_DEFAULT_HVAC_MODE: HVACMode.COOL,
            CONF_OFF_BEHAVIOR: OFF_BEHAVIOR_IGNORE,
            CONF_APPLY_ON_START: False,
            CONF_LEGACY_ON_TIME: "06:00:00",
            CONF_LEGACY_OFF_TIME: "22:00:00",
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 3

    room = RoomConfig.from_entry(entry)
    target = room.targets[0]
    assert target.key == entry.entry_id

    # The old schedule helper becomes the Default plan's schedule for the target.
    assert room.plan_names == (DEFAULT_PLAN_NAME,)
    assert room.plans[0].schedule_for(target.key) == SCHEDULE_ENTITY_ID

    # Behaviour flags carry over verbatim.
    behavior = room.behavior_for(target.key)
    assert behavior.schedule_enabled is True
    assert behavior.default_hvac_mode == HVACMode.COOL
    assert behavior.off_behavior == OFF_BEHAVIOR_IGNORE
    assert behavior.apply_on_start is False

    assert room.legacy_on_time == "06:00:00"
    assert room.legacy_off_time == "22:00:00"


async def test_migrates_version_2_without_schedule_still_creates_default_plan(
    hass: HomeAssistant,
) -> None:
    """Test a Default plan is created even when nothing was ever linked."""
    _set_target(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title="Living Room",
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID},
        options={
            CONF_SCHEDULE_ENABLED: False,
            CONF_OFF_BEHAVIOR: DEFAULT_OFF_BEHAVIOR,
            CONF_APPLY_ON_START: DEFAULT_APPLY_ON_START,
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 3

    room = RoomConfig.from_entry(entry)
    target = room.targets[0]
    assert target.key == entry.entry_id
    assert room.plan_names == (DEFAULT_PLAN_NAME,)
    assert room.plans[0].schedules == {}
    assert room.legacy_on_time is None
    assert room.legacy_off_time is None

    # No linked schedule and no legacy times means no linked-schedule repair.
    assert (
        ir.async_get(hass).async_get_issue(
            DOMAIN, f"{ISSUE_SCHEDULE_NOT_LINKED}_{entry.entry_id}_{target.key}"
        )
        is None
    )


async def test_migrates_version_2_without_a_target_entity_id(
    hass: HomeAssistant,
) -> None:
    """A v2 entry that never had a target still becomes a valid empty room."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title="Empty Room",
        data={CONF_NAME: "Empty Room"},
        options={CONF_SCHEDULE_ENABLED: False},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 3
    room = RoomConfig.from_entry(entry)
    # No target survives, but the room is still given its Default plan.
    assert room.targets == ()
    assert room.plan_names == (DEFAULT_PLAN_NAME,)
    assert room.behaviors == {}


async def test_entry_already_at_version_3_is_untouched(hass: HomeAssistant) -> None:
    """A current-version entry migrates as a no-op, unchanged."""
    _set_target(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        title="Living Room",
        data={CONF_NAME: "Living Room", "targets": []},
        options={"plans": []},
    )
    entry.add_to_hass(hass)
    data_before = dict(entry.data)
    options_before = dict(entry.options)

    assert await async_migrate_entry(hass, entry) is True

    assert entry.version == 3
    assert dict(entry.data) == data_before
    assert dict(entry.options) == options_before


async def test_entry_from_a_newer_version_is_rejected(hass: HomeAssistant) -> None:
    """An entry created by a newer release cannot be downgraded."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=4,
        title="Living Room",
        data={CONF_NAME: "Living Room"},
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is False
