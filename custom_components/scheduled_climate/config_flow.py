"""Config flow for Scheduled Climate."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.climate import ATTR_HVAC_MODES, HVACMode
from homeassistant.components.schedule import DOMAIN as SCHEDULE_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    IconSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_APPLY_ON_START,
    CONF_DEFAULT_HVAC_MODE,
    CONF_HIDE_TARGETS,
    CONF_HYSTERESIS,
    CONF_OFF_BEHAVIOR,
    CONF_OUTDOOR_TEMP_ENTITY_ID,
    CONF_OVERRIDE_DEFAULT_MINUTES,
    CONF_OVERRIDE_MAX_MINUTES,
    CONF_PLAN_ICON,
    CONF_PLAN_MAX_OUTDOOR_TEMP,
    CONF_PLAN_MIN_OUTDOOR_TEMP,
    CONF_PLAN_SELECTION_MODE,
    CONF_SCHEDULE_ENABLED,
    CONF_SCHEDULE_ENTITY_ID,
    CONF_SUSTAIN_MINUTES,
    CONF_TARGET_ENTITY_ID,
    CONF_TARGETS,
    DEFAULT_PLAN_NAME,
    DOMAIN,
    OFF_BEHAVIORS,
    PLAN_MODE_OUTDOOR_TEMP,
    PLAN_MODES,
)
from .models import (
    OverrideConfig,
    PlanConfig,
    PlanSelectionConfig,
    RoomConfig,
    TargetBehavior,
    TargetConfig,
    build_options,
    new_key,
    options_from_config,
    targets_as_data,
)
from .visibility import async_unhide_targets

CONF_TARGET = "target"
CONF_PLAN = "plan"
CONF_REMOVE = "remove"

OPTIONS_MENU = (
    "add_target",
    "edit_target",
    "add_plan",
    "edit_plan",
    "link_schedule",
    "plan_selection",
    "override",
    "visibility",
)


def _entity_name(hass: HomeAssistant, entity_id: str, fallback: str) -> str:
    """Return a friendly name for an entity, falling back when unknown."""
    state = hass.states.get(entity_id)
    if state is None:
        return fallback
    name = state.attributes.get("friendly_name")
    return str(name) if name else fallback


def _hvac_modes(hass: HomeAssistant, entity_id: str | None) -> list[str]:
    """Return the on modes a target offers, or every standard mode."""
    state = hass.states.get(entity_id) if entity_id else None
    modes = [
        mode
        for mode in (state.attributes.get(ATTR_HVAC_MODES, []) if state else [])
        if mode != HVACMode.OFF
    ]
    return modes or [mode for mode in HVACMode if mode is not HVACMode.OFF]


def _target_error(
    hass: HomeAssistant,
    entity_id: str,
    *,
    current_entry_id: str | None,
    room: RoomConfig | None = None,
    allow_key: str | None = None,
) -> str | None:
    """Return a validation error for a chosen climate entity, if any."""
    if hass.states.get(entity_id) is None:
        return "target_not_found"

    registry_entry = er.async_get(hass).async_get(entity_id)
    if registry_entry is not None and registry_entry.platform == DOMAIN:
        return "target_is_scheduled_climate"

    if room is not None:
        clash = room.target_by_entity_id(entity_id)
        if clash is not None and clash.key != allow_key:
            return "target_already_configured"

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == current_entry_id:
            continue
        other = RoomConfig.from_entry(entry)
        if other.target_by_entity_id(entity_id) is not None:
            return "target_already_configured"

    return None


def _temperature_selector() -> NumberSelector:
    """Return the selector used for an outdoor temperature bound."""
    return NumberSelector(
        NumberSelectorConfig(min=-80, max=80, step=0.5, mode=NumberSelectorMode.BOX)
    )


def _initial_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the schema that creates a room around its first target."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_NAME, default=defaults.get(CONF_NAME, "Scheduled Climate")
            ): str,
            vol.Required(
                CONF_TARGET_ENTITY_ID,
                default=defaults.get(CONF_TARGET_ENTITY_ID, vol.UNDEFINED),
            ): EntitySelector(EntitySelectorConfig(domain=Platform.CLIMATE)),
        }
    )


class ScheduledClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Scheduled Climate."""

    VERSION = 3

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> ScheduledClimateOptionsFlow:
        """Return the options flow handler."""
        return ScheduledClimateOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Create a room around its first climate entity."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id = user_input[CONF_TARGET_ENTITY_ID]
            if error := _target_error(self.hass, entity_id, current_entry_id=None):
                errors[CONF_TARGET_ENTITY_ID] = error
            else:
                name = user_input[CONF_NAME]
                target = TargetConfig(
                    key=new_key(),
                    entity_id=entity_id,
                    name=_entity_name(self.hass, entity_id, name),
                )
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_NAME: name,
                        CONF_TARGETS: targets_as_data([target]),
                    },
                    options=build_options(
                        behaviors={target.key: TargetBehavior()},
                        plans=[PlanConfig(id=new_key(), name=DEFAULT_PLAN_NAME)],
                        plan_selection=PlanSelectionConfig(),
                        override=OverrideConfig(),
                    ),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_initial_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Rename the room. Its climate entities are managed from the options."""
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            return self.async_update_reload_and_abort(
                entry,
                data_updates={CONF_NAME: user_input[CONF_NAME]},
                title=user_input[CONF_NAME],
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=entry.data.get(CONF_NAME, entry.title)
                    ): str
                }
            ),
        )


class ScheduledClimateOptionsFlow(config_entries.OptionsFlow):
    """Manage the targets, plans and plan selection of one room."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._target_key: str | None = None
        self._plan_id: str | None = None

    @property
    def room(self) -> RoomConfig:
        """Return the current room configuration."""
        return RoomConfig.from_entry(self.config_entry)

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show what can be configured for this room."""
        room = self.room
        menu_options = [
            option
            for option in OPTIONS_MENU
            if not (option == "edit_target" and not room.targets)
            and not (option == "edit_plan" and not room.plans)
            and not (option == "link_schedule" and not (room.targets and room.plans))
        ]
        return self.async_show_menu(step_id="init", menu_options=menu_options)

    # ------------------------------------------------------------------
    # Targets
    # ------------------------------------------------------------------

    async def async_step_add_target(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add another climate entity to the room."""
        room = self.room
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id = user_input[CONF_TARGET_ENTITY_ID]
            error = _target_error(
                self.hass,
                entity_id,
                current_entry_id=self.config_entry.entry_id,
                room=room,
            )
            if error:
                errors[CONF_TARGET_ENTITY_ID] = error
            else:
                target = TargetConfig(
                    key=new_key(),
                    entity_id=entity_id,
                    name=user_input.get(CONF_NAME)
                    or _entity_name(self.hass, entity_id, entity_id),
                )
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        **self.config_entry.data,
                        CONF_TARGETS: targets_as_data([*room.targets, target]),
                    },
                )
                behaviors = dict(room.behaviors)
                behaviors[target.key] = TargetBehavior()
                return self.async_create_entry(
                    data=options_from_config(room, behaviors=behaviors)
                )

        return self.async_show_form(
            step_id="add_target",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TARGET_ENTITY_ID): EntitySelector(
                        EntitySelectorConfig(domain=Platform.CLIMATE)
                    ),
                    vol.Optional(CONF_NAME): TextSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_edit_target(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick which climate entity to edit."""
        room = self.room
        if not room.targets:
            return self.async_abort(reason="no_targets")

        if user_input is not None:
            self._target_key = user_input[CONF_TARGET]
            return await self.async_step_target_options()

        return self.async_show_form(
            step_id="edit_target",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TARGET): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=target.key, label=target.name)
                                for target in room.targets
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_target_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit or remove one climate entity."""
        room = self.room
        target = room.target_by_key(self._target_key or "")
        if target is None:
            return self.async_abort(reason="no_targets")

        errors: dict[str, str] = {}
        behavior = room.behavior_for(target.key)

        if user_input is not None:
            if user_input.get(CONF_REMOVE):
                if len(room.targets) <= 1:
                    errors["base"] = "last_target"
                else:
                    return self._remove_target(room, target)
            else:
                entity_id = user_input[CONF_TARGET_ENTITY_ID]
                error = _target_error(
                    self.hass,
                    entity_id,
                    current_entry_id=self.config_entry.entry_id,
                    room=room,
                    allow_key=target.key,
                )
                if error:
                    errors[CONF_TARGET_ENTITY_ID] = error
                else:
                    return self._save_target(room, target, user_input)

        return self.async_show_form(
            step_id="target_options",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=target.name): TextSelector(),
                    vol.Required(
                        CONF_TARGET_ENTITY_ID, default=target.entity_id
                    ): EntitySelector(EntitySelectorConfig(domain=Platform.CLIMATE)),
                    vol.Required(
                        CONF_SCHEDULE_ENABLED, default=behavior.schedule_enabled
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_DEFAULT_HVAC_MODE, default=behavior.default_hvac_mode
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=_hvac_modes(self.hass, target.entity_id),
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="hvac_mode",
                        )
                    ),
                    vol.Required(
                        CONF_OFF_BEHAVIOR, default=behavior.off_behavior
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=list(OFF_BEHAVIORS),
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="off_behavior",
                        )
                    ),
                    vol.Required(
                        CONF_APPLY_ON_START, default=behavior.apply_on_start
                    ): BooleanSelector(),
                    vol.Required(CONF_REMOVE, default=False): BooleanSelector(),
                }
            ),
            errors=errors,
            description_placeholders={"name": target.name},
        )

    def _save_target(
        self, room: RoomConfig, target: TargetConfig, user_input: dict[str, Any]
    ) -> FlowResult:
        """Persist edits to one target."""
        updated = TargetConfig(
            key=target.key,
            entity_id=user_input[CONF_TARGET_ENTITY_ID],
            name=user_input[CONF_NAME] or target.name,
        )
        targets = [
            updated if existing.key == target.key else existing
            for existing in room.targets
        ]
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={**self.config_entry.data, CONF_TARGETS: targets_as_data(targets)},
        )

        if updated.entity_id != target.entity_id:
            # The old entity is no longer wrapped; the new one now is.
            async_unhide_targets(self.hass, [target.entity_id])

        behaviors = dict(room.behaviors)
        behaviors[target.key] = TargetBehavior(
            schedule_enabled=user_input[CONF_SCHEDULE_ENABLED],
            default_hvac_mode=user_input[CONF_DEFAULT_HVAC_MODE],
            off_behavior=user_input[CONF_OFF_BEHAVIOR],
            apply_on_start=user_input[CONF_APPLY_ON_START],
        )
        return self.async_create_entry(
            data=options_from_config(room, behaviors=behaviors)
        )

    def _remove_target(self, room: RoomConfig, target: TargetConfig) -> FlowResult:
        """Drop one target, leaving its schedule helpers untouched."""
        targets = [existing for existing in room.targets if existing.key != target.key]
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={**self.config_entry.data, CONF_TARGETS: targets_as_data(targets)},
        )

        # Nothing wraps this entity any more, so it must become visible again.
        async_unhide_targets(self.hass, [target.entity_id])

        behaviors = {
            key: behavior
            for key, behavior in room.behaviors.items()
            if key != target.key
        }
        plans = [plan.with_schedule(target.key, None) for plan in room.plans]
        return self.async_create_entry(
            data=options_from_config(room, behaviors=behaviors, plans=plans)
        )

    # ------------------------------------------------------------------
    # Plans
    # ------------------------------------------------------------------

    async def async_step_add_plan(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a named plan to the room."""
        room = self.room
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            minimum = user_input.get(CONF_PLAN_MIN_OUTDOOR_TEMP)
            maximum = user_input.get(CONF_PLAN_MAX_OUTDOOR_TEMP)
            if room.plan_by_name(name) is not None:
                errors[CONF_NAME] = "plan_name_taken"
            elif minimum is not None and maximum is not None and minimum >= maximum:
                errors["base"] = "plan_band_inverted"
            else:
                plan = PlanConfig(
                    id=new_key(),
                    name=name,
                    icon=user_input.get(CONF_PLAN_ICON) or None,
                    min_outdoor_temp=minimum,
                    max_outdoor_temp=maximum,
                )
                return self.async_create_entry(
                    data=options_from_config(room, plans=[*room.plans, plan])
                )

        return self.async_show_form(
            step_id="add_plan",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): TextSelector(),
                    vol.Optional(CONF_PLAN_ICON): IconSelector(),
                    vol.Optional(CONF_PLAN_MIN_OUTDOOR_TEMP): _temperature_selector(),
                    vol.Optional(CONF_PLAN_MAX_OUTDOOR_TEMP): _temperature_selector(),
                }
            ),
            errors=errors,
        )

    async def async_step_edit_plan(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick which plan to edit."""
        room = self.room
        if not room.plans:
            return self.async_abort(reason="no_plans")

        if user_input is not None:
            self._plan_id = user_input[CONF_PLAN]
            return await self.async_step_plan_options()

        return self.async_show_form(
            step_id="edit_plan",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PLAN): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=plan.id, label=plan.name)
                                for plan in room.plans
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_plan_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit or delete one plan."""
        room = self.room
        plan = room.plan_by_id(self._plan_id)
        if plan is None:
            return self.async_abort(reason="no_plans")

        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get(CONF_REMOVE):
                if len(room.plans) <= 1:
                    errors["base"] = "last_plan"
                else:
                    plans = [
                        existing for existing in room.plans if existing.id != plan.id
                    ]
                    return self.async_create_entry(
                        data=options_from_config(room, plans=plans)
                    )
            else:
                name = user_input[CONF_NAME].strip()
                clash = room.plan_by_name(name)
                minimum = user_input.get(CONF_PLAN_MIN_OUTDOOR_TEMP)
                maximum = user_input.get(CONF_PLAN_MAX_OUTDOOR_TEMP)
                if clash is not None and clash.id != plan.id:
                    errors[CONF_NAME] = "plan_name_taken"
                elif minimum is not None and maximum is not None and minimum >= maximum:
                    errors["base"] = "plan_band_inverted"
                else:
                    updated = replace(
                        plan,
                        name=name,
                        icon=user_input.get(CONF_PLAN_ICON) or None,
                        min_outdoor_temp=minimum,
                        max_outdoor_temp=maximum,
                    )
                    plans = [
                        updated if existing.id == plan.id else existing
                        for existing in room.plans
                    ]
                    return self.async_create_entry(
                        data=options_from_config(room, plans=plans)
                    )

        schema: dict[vol.Marker, Any] = {
            vol.Required(CONF_NAME, default=plan.name): TextSelector(),
            vol.Optional(
                CONF_PLAN_ICON, default=plan.icon or vol.UNDEFINED
            ): IconSelector(),
            vol.Optional(
                CONF_PLAN_MIN_OUTDOOR_TEMP,
                default=(
                    plan.min_outdoor_temp
                    if plan.min_outdoor_temp is not None
                    else vol.UNDEFINED
                ),
            ): _temperature_selector(),
            vol.Optional(
                CONF_PLAN_MAX_OUTDOOR_TEMP,
                default=(
                    plan.max_outdoor_temp
                    if plan.max_outdoor_temp is not None
                    else vol.UNDEFINED
                ),
            ): _temperature_selector(),
            vol.Required(CONF_REMOVE, default=False): BooleanSelector(),
        }
        return self.async_show_form(
            step_id="plan_options",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={"name": plan.name},
        )

    # ------------------------------------------------------------------
    # Schedule helpers
    # ------------------------------------------------------------------

    async def async_step_link_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Point one target and plan at a schedule helper."""
        room = self.room
        if not room.targets:
            return self.async_abort(reason="no_targets")
        if not room.plans:
            return self.async_abort(reason="no_plans")

        errors: dict[str, str] = {}

        if user_input is not None:
            plan = room.plan_by_id(user_input[CONF_PLAN])
            target_key = user_input[CONF_TARGET]
            schedule_entity_id = user_input.get(CONF_SCHEDULE_ENTITY_ID) or None
            if plan is None or room.target_by_key(target_key) is None:
                errors["base"] = "target_not_found"
            elif (
                schedule_entity_id is not None
                and self.hass.states.get(schedule_entity_id) is None
            ):
                errors[CONF_SCHEDULE_ENTITY_ID] = "schedule_not_found"
            else:
                updated = plan.with_schedule(target_key, schedule_entity_id)
                plans = [
                    updated if existing.id == plan.id else existing
                    for existing in room.plans
                ]
                return self.async_create_entry(
                    data=options_from_config(room, plans=plans)
                )

        return self.async_show_form(
            step_id="link_schedule",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TARGET): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=target.key, label=target.name)
                                for target in room.targets
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_PLAN): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=plan.id, label=plan.name)
                                for plan in room.plans
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(CONF_SCHEDULE_ENTITY_ID): EntitySelector(
                        EntitySelectorConfig(domain=SCHEDULE_DOMAIN)
                    ),
                }
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Plan selection and holds
    # ------------------------------------------------------------------

    async def async_step_plan_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose how the active plan is picked."""
        room = self.room
        selection = room.plan_selection
        errors: dict[str, str] = {}

        if user_input is not None:
            mode = user_input[CONF_PLAN_SELECTION_MODE]
            outdoor = user_input.get(CONF_OUTDOOR_TEMP_ENTITY_ID) or None
            if mode == PLAN_MODE_OUTDOOR_TEMP and outdoor is None:
                errors[CONF_OUTDOOR_TEMP_ENTITY_ID] = "outdoor_sensor_required"
            else:
                return self.async_create_entry(
                    data=options_from_config(
                        room,
                        plan_selection=PlanSelectionConfig(
                            mode=mode,
                            outdoor_temp_entity_id=outdoor,
                            hysteresis=float(user_input[CONF_HYSTERESIS]),
                            sustain_minutes=int(user_input[CONF_SUSTAIN_MINUTES]),
                        ),
                    )
                )

        return self.async_show_form(
            step_id="plan_selection",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PLAN_SELECTION_MODE, default=selection.mode
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=list(PLAN_MODES),
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="plan_selection_mode",
                        )
                    ),
                    vol.Optional(
                        CONF_OUTDOOR_TEMP_ENTITY_ID,
                        default=selection.outdoor_temp_entity_id or vol.UNDEFINED,
                    ): EntitySelector(
                        EntitySelectorConfig(
                            domain=[Platform.SENSOR, Platform.NUMBER, "input_number"]
                        )
                    ),
                    vol.Required(
                        CONF_HYSTERESIS, default=selection.hysteresis
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=0, max=20, step=0.5, mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(
                        CONF_SUSTAIN_MINUTES, default=selection.sustain_minutes
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=0, max=1440, step=5, mode=NumberSelectorMode.BOX
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_override(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Set the bounds every temporary hold must respect."""
        room = self.room
        override = room.override
        errors: dict[str, str] = {}

        if user_input is not None:
            default_minutes = int(user_input[CONF_OVERRIDE_DEFAULT_MINUTES])
            max_minutes = int(user_input[CONF_OVERRIDE_MAX_MINUTES])
            if default_minutes > max_minutes:
                errors["base"] = "override_bounds"
            else:
                return self.async_create_entry(
                    data=options_from_config(
                        room,
                        override=OverrideConfig(
                            default_minutes=default_minutes,
                            max_minutes=max_minutes,
                        ),
                    )
                )

        return self.async_show_form(
            step_id="override",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_OVERRIDE_DEFAULT_MINUTES,
                        default=override.default_minutes,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1, max=1440, step=5, mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(
                        CONF_OVERRIDE_MAX_MINUTES, default=override.max_minutes
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1, max=1440, step=5, mode=NumberSelectorMode.BOX
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_visibility(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose whether the wrapped climate entities stay visible.

        Each target is mirrored by a wrapper entity, so leaving both visible
        shows every thermostat twice. Hiding only affects the user interface;
        automations, history and the APIs keep addressing the wrapped entity.
        """
        room = self.room

        if user_input is not None:
            return self.async_create_entry(
                data=options_from_config(
                    room, hide_targets=bool(user_input[CONF_HIDE_TARGETS])
                )
            )

        return self.async_show_form(
            step_id="visibility",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HIDE_TARGETS, default=room.hide_targets
                    ): BooleanSelector()
                }
            ),
        )
