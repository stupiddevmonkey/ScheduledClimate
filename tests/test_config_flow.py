"""Tests for the Scheduled Climate config and options flow."""

import pytest
from conftest import make_room_entry, make_target
from homeassistant import config_entries
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate import HVACMode
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.loader import async_get_integration
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scheduled_climate.config_flow import (
    CONF_PLAN,
    CONF_REMOVE,
    CONF_TARGET,
)
from custom_components.scheduled_climate.const import (
    CONF_APPLY_ON_START,
    CONF_DEFAULT_HVAC_MODE,
    CONF_HYSTERESIS,
    CONF_OFF_BEHAVIOR,
    CONF_OUTDOOR_TEMP_ENTITY_ID,
    CONF_OVERRIDE_DEFAULT_MINUTES,
    CONF_OVERRIDE_MAX_MINUTES,
    CONF_PLAN_NAME,
    CONF_PLAN_SELECTION_MODE,
    CONF_PLANS,
    CONF_SCHEDULE_ENABLED,
    CONF_SCHEDULE_ENTITY_ID,
    CONF_SUSTAIN_MINUTES,
    CONF_TARGET_ENTITY_ID,
    CONF_TARGETS,
    DEFAULT_PLAN_NAME,
    DOMAIN,
    OFF_BEHAVIOR_TURN_OFF,
    PLAN_MODE_MANUAL,
    PLAN_MODE_OUTDOOR_TEMP,
)
from custom_components.scheduled_climate.models import PlanConfig, RoomConfig

TARGET_ENTITY_ID = "climate.living_room"
SECOND_TARGET_ID = "climate.bedroom"
SCHEDULE_ENTITY_ID = "schedule.office"
TARGET_KEY = "living-room-key"
BEDROOM_KEY = "bedroom-key"
PLAN_ID = "plan-default"


async def test_integration_is_visible_on_integrations_dashboard(
    hass: HomeAssistant,
) -> None:
    """Test the integration is not classified as a hidden helper."""
    integration = await async_get_integration(hass, DOMAIN)

    assert integration.integration_type == "service"


# ----------------------------------------------------------------------
# User flow
# ----------------------------------------------------------------------


async def _start_user_flow(hass: HomeAssistant) -> config_entries.ConfigFlowResult:
    """Start a user config flow."""
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )


async def test_user_flow_creates_room(hass: HomeAssistant) -> None:
    """Test the user step creates a room, its first target and a Default plan."""
    hass.states.async_set(TARGET_ENTITY_ID, HVACMode.HEAT)

    result = await _start_user_flow(hass)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Living Room", CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living Room"

    data = result["data"]
    assert data[CONF_NAME] == "Living Room"
    assert len(data[CONF_TARGETS]) == 1
    assert data[CONF_TARGETS][0][CONF_TARGET_ENTITY_ID] == TARGET_ENTITY_ID

    plans = result["options"][CONF_PLANS]
    assert [plan[CONF_PLAN_NAME] for plan in plans] == [DEFAULT_PLAN_NAME]


async def test_user_flow_rejects_missing_target(hass: HomeAssistant) -> None:
    """Test rejecting a target that does not exist."""
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Missing", CONF_TARGET_ENTITY_ID: "climate.missing"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TARGET_ENTITY_ID: "target_not_found"}


async def test_user_flow_rejects_scheduled_climate_target(
    hass: HomeAssistant,
) -> None:
    """Test preventing wrappers from targeting other wrappers."""
    registry = er.async_get(hass)
    wrapper = registry.async_get_or_create(CLIMATE_DOMAIN, DOMAIN, "wrapper")
    hass.states.async_set(wrapper.entity_id, HVACMode.HEAT)

    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Nested", CONF_TARGET_ENTITY_ID: wrapper.entity_id},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TARGET_ENTITY_ID: "target_is_scheduled_climate"}


async def test_user_flow_rejects_duplicate_target(hass: HomeAssistant) -> None:
    """Test preventing a target already used by another room."""
    hass.states.async_set(TARGET_ENTITY_ID, HVACMode.HEAT)
    make_room_entry(
        title="Existing",
        targets=[make_target(TARGET_ENTITY_ID, "Living Room", key=TARGET_KEY)],
    ).add_to_hass(hass)

    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Duplicate", CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TARGET_ENTITY_ID: "target_already_configured"}


async def test_reconfigure_renames_room(hass: HomeAssistant) -> None:
    """Test reconfiguration only renames the room."""
    hass.states.async_set(TARGET_ENTITY_ID, HVACMode.HEAT)
    entry = make_room_entry(
        title="Living Room",
        targets=[make_target(TARGET_ENTITY_ID, "Living Room", key=TARGET_KEY)],
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Lounge"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.title == "Lounge"
    assert entry.data[CONF_NAME] == "Lounge"
    # The target list is untouched by a rename.
    assert entry.data[CONF_TARGETS][0][CONF_TARGET_ENTITY_ID] == TARGET_ENTITY_ID


# ----------------------------------------------------------------------
# Options flow
# ----------------------------------------------------------------------


def _single_target_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return an added one-target, one-plan room entry."""
    hass.states.async_set(TARGET_ENTITY_ID, HVACMode.HEAT)
    entry = make_room_entry(
        title="Living Room",
        targets=[make_target(TARGET_ENTITY_ID, "Living Room", key=TARGET_KEY)],
        plans=[PlanConfig(id=PLAN_ID, name=DEFAULT_PLAN_NAME)],
    )
    entry.add_to_hass(hass)
    return entry


async def test_options_menu_lists_steps(hass: HomeAssistant) -> None:
    """Test the options flow opens a menu of what can be configured."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) >= {
        "add_target",
        "edit_target",
        "add_plan",
        "edit_plan",
        "link_schedule",
        "plan_selection",
        "override",
    }


async def test_options_add_target(hass: HomeAssistant) -> None:
    """Test adding another climate entity to the room."""
    entry = _single_target_entry(hass)
    hass.states.async_set(SECOND_TARGET_ID, HVACMode.HEAT)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_target"}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_TARGET_ENTITY_ID: SECOND_TARGET_ID, CONF_NAME: "Bedroom"},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    room = RoomConfig.from_entry(entry)
    assert {target.entity_id for target in room.targets} == {
        TARGET_ENTITY_ID,
        SECOND_TARGET_ID,
    }


async def test_options_edit_target(hass: HomeAssistant) -> None:
    """Test editing one target's behaviour."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_target"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_TARGET: TARGET_KEY}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Lounge",
            CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID,
            CONF_SCHEDULE_ENABLED: True,
            CONF_DEFAULT_HVAC_MODE: HVACMode.HEAT,
            CONF_OFF_BEHAVIOR: OFF_BEHAVIOR_TURN_OFF,
            CONF_APPLY_ON_START: True,
            CONF_REMOVE: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    room = RoomConfig.from_entry(entry)
    assert room.target_by_key(TARGET_KEY).name == "Lounge"
    assert room.behavior_for(TARGET_KEY).schedule_enabled is True


async def test_options_remove_last_target_is_rejected(hass: HomeAssistant) -> None:
    """Test the only target cannot be removed."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_target"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_TARGET: TARGET_KEY}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Living Room",
            CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID,
            CONF_SCHEDULE_ENABLED: False,
            CONF_DEFAULT_HVAC_MODE: HVACMode.HEAT,
            CONF_OFF_BEHAVIOR: OFF_BEHAVIOR_TURN_OFF,
            CONF_APPLY_ON_START: True,
            CONF_REMOVE: True,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "last_target"}


async def test_options_remove_target(hass: HomeAssistant) -> None:
    """Test removing a target from a multi-target room."""
    hass.states.async_set(TARGET_ENTITY_ID, HVACMode.HEAT)
    hass.states.async_set(SECOND_TARGET_ID, HVACMode.HEAT)
    entry = make_room_entry(
        title="Home",
        targets=[
            make_target(TARGET_ENTITY_ID, "Living Room", key=TARGET_KEY),
            make_target(SECOND_TARGET_ID, "Bedroom", key=BEDROOM_KEY),
        ],
        plans=[PlanConfig(id=PLAN_ID, name=DEFAULT_PLAN_NAME)],
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_target"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_TARGET: BEDROOM_KEY}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Bedroom",
            CONF_TARGET_ENTITY_ID: SECOND_TARGET_ID,
            CONF_SCHEDULE_ENABLED: False,
            CONF_DEFAULT_HVAC_MODE: HVACMode.HEAT,
            CONF_OFF_BEHAVIOR: OFF_BEHAVIOR_TURN_OFF,
            CONF_APPLY_ON_START: True,
            CONF_REMOVE: True,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    room = RoomConfig.from_entry(entry)
    assert [target.key for target in room.targets] == [TARGET_KEY]


async def test_options_add_plan(hass: HomeAssistant) -> None:
    """Test adding a named plan to the room."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_plan"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_NAME: "Night"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    room = RoomConfig.from_entry(entry)
    assert set(room.plan_names) == {DEFAULT_PLAN_NAME, "Night"}


async def test_options_add_plan_rejects_duplicate_name(hass: HomeAssistant) -> None:
    """Test a plan cannot reuse an existing plan name."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_plan"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_NAME: DEFAULT_PLAN_NAME}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_NAME: "plan_name_taken"}


async def test_options_edit_plan_renames(hass: HomeAssistant) -> None:
    """Test renaming a plan."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_plan"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_PLAN: PLAN_ID}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_PLAN_NAME: "Winter", CONF_REMOVE: False}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    room = RoomConfig.from_entry(entry)
    assert room.plan_names == ("Winter",)


async def test_options_remove_last_plan_is_rejected(hass: HomeAssistant) -> None:
    """Test the only plan cannot be removed."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_plan"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_PLAN: PLAN_ID}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_PLAN_NAME: DEFAULT_PLAN_NAME, CONF_REMOVE: True}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "last_plan"}


async def test_options_link_schedule(hass: HomeAssistant) -> None:
    """Test pointing a target and plan at a schedule helper."""
    entry = _single_target_entry(hass)
    hass.states.async_set(SCHEDULE_ENTITY_ID, "off")

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "link_schedule"}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TARGET: TARGET_KEY,
            CONF_PLAN: PLAN_ID,
            CONF_SCHEDULE_ENTITY_ID: SCHEDULE_ENTITY_ID,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    room = RoomConfig.from_entry(entry)
    assert room.plan_by_id(PLAN_ID).schedule_for(TARGET_KEY) == SCHEDULE_ENTITY_ID


async def test_options_plan_selection_requires_outdoor_sensor(
    hass: HomeAssistant,
) -> None:
    """Test the outdoor-temperature mode needs a sensor."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "plan_selection"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_PLAN_SELECTION_MODE: PLAN_MODE_OUTDOOR_TEMP,
            CONF_HYSTERESIS: 2.0,
            CONF_SUSTAIN_MINUTES: 30,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_OUTDOOR_TEMP_ENTITY_ID: "outdoor_sensor_required"}


async def test_options_plan_selection_saves_manual_mode(hass: HomeAssistant) -> None:
    """Test saving the plan selection rule."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "plan_selection"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_PLAN_SELECTION_MODE: PLAN_MODE_MANUAL,
            CONF_HYSTERESIS: 3.0,
            CONF_SUSTAIN_MINUTES: 15,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    room = RoomConfig.from_entry(entry)
    assert room.plan_selection.mode == PLAN_MODE_MANUAL
    assert room.plan_selection.hysteresis == 3.0
    assert room.plan_selection.sustain_minutes == 15


async def test_options_override_bounds_rejected(hass: HomeAssistant) -> None:
    """Test a default hold longer than the maximum is rejected."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "override"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_OVERRIDE_DEFAULT_MINUTES: 200, CONF_OVERRIDE_MAX_MINUTES: 100},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "override_bounds"}


async def test_options_override_saves_bounds(hass: HomeAssistant) -> None:
    """Test saving valid hold bounds."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "override"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_OVERRIDE_DEFAULT_MINUTES: 60, CONF_OVERRIDE_MAX_MINUTES: 240},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    room = RoomConfig.from_entry(entry)
    assert room.override.default_minutes == 60
    assert room.override.max_minutes == 240


# ----------------------------------------------------------------------
# Awkward plan and target edits
# ----------------------------------------------------------------------


async def _open_plan_options(
    hass: HomeAssistant, entry: MockConfigEntry, plan_id: str
) -> config_entries.ConfigFlowResult:
    """Open the edit form for one plan."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_plan"}
    )
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_PLAN: plan_id}
    )


@pytest.mark.parametrize("name", ["  default  ", "DEFAULT", "Default "])
async def test_options_add_plan_rejects_case_or_whitespace_duplicate(
    hass: HomeAssistant, name: str
) -> None:
    """A new plan name that only differs by case or padding is refused."""
    entry = _single_target_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_plan"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_NAME: name}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_NAME: "plan_name_taken"}


async def test_options_edit_plan_rejects_case_duplicate_of_another_plan(
    hass: HomeAssistant,
) -> None:
    """Renaming a plan onto another plan's name (case-insensitively) is refused."""
    hass.states.async_set(TARGET_ENTITY_ID, HVACMode.HEAT)
    entry = make_room_entry(
        title="Living Room",
        targets=[make_target(TARGET_ENTITY_ID, "Living Room", key=TARGET_KEY)],
        plans=[
            PlanConfig(id="winter", name="Winter"),
            PlanConfig(id="summer", name="Summer"),
        ],
    )
    entry.add_to_hass(hass)

    result = await _open_plan_options(hass, entry, "summer")
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_PLAN_NAME: "  winter  ", CONF_REMOVE: False}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_NAME: "plan_name_taken"}


async def test_options_delete_the_selected_plan(hass: HomeAssistant) -> None:
    """Deleting a plan (even the selected one) succeeds and leaves the rest.

    The config flow does not track which plan the select entity sits on; that
    fallback is the plan selector's job at runtime.
    """
    hass.states.async_set(TARGET_ENTITY_ID, HVACMode.HEAT)
    entry = make_room_entry(
        title="Living Room",
        targets=[make_target(TARGET_ENTITY_ID, "Living Room", key=TARGET_KEY)],
        plans=[
            PlanConfig(id="winter", name="Winter"),
            PlanConfig(id="summer", name="Summer"),
        ],
    )
    entry.add_to_hass(hass)

    result = await _open_plan_options(hass, entry, "summer")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_PLAN_NAME: "Summer", CONF_REMOVE: True}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    room = RoomConfig.from_entry(entry)
    assert room.plan_names == ("Winter",)


async def test_options_edit_target_rejects_entity_owned_by_another_room(
    hass: HomeAssistant,
) -> None:
    """Re-pointing a target at an entity another room owns is refused."""
    hass.states.async_set(TARGET_ENTITY_ID, HVACMode.HEAT)
    hass.states.async_set(SECOND_TARGET_ID, HVACMode.HEAT)

    entry = make_room_entry(
        title="Living Room",
        targets=[make_target(TARGET_ENTITY_ID, "Living Room", key=TARGET_KEY)],
        plans=[PlanConfig(id=PLAN_ID, name=DEFAULT_PLAN_NAME)],
    )
    entry.add_to_hass(hass)
    # A second room already owns the bedroom climate entity.
    make_room_entry(
        title="Bedroom",
        targets=[make_target(SECOND_TARGET_ID, "Bedroom", key=BEDROOM_KEY)],
    ).add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_target"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_TARGET: TARGET_KEY}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Living Room",
            CONF_TARGET_ENTITY_ID: SECOND_TARGET_ID,
            CONF_SCHEDULE_ENABLED: False,
            CONF_DEFAULT_HVAC_MODE: HVACMode.HEAT,
            CONF_OFF_BEHAVIOR: OFF_BEHAVIOR_TURN_OFF,
            CONF_APPLY_ON_START: True,
            CONF_REMOVE: False,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TARGET_ENTITY_ID: "target_already_configured"}
