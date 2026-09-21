"""Scheduled Climate wrapper entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components.climate import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    ATTR_HUMIDITY,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    ATTR_SWING_HORIZONTAL_MODE,
    ATTR_SWING_HORIZONTAL_MODES,
    ATTR_SWING_MODE,
    ATTR_SWING_MODES,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TEMPERATURE,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_SWING_HORIZONTAL_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import EventEntityRegistryUpdatedData
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
)
from homeassistant.util import dt as dt_util

from .block import ScheduleBlock
from .const import (
    ATTR_ACTIVE_PLAN,
    ATTR_ACTIVE_SCHEDULE_BLOCK,
    ATTR_DURATION,
    ATTR_LEGACY_SCHEDULE,
    ATTR_MAX_HUMIDITY,
    ATTR_MAX_TEMP,
    ATTR_MIN_HUMIDITY,
    ATTR_MIN_TEMP,
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
    ATTR_TARGET_HUMIDITY_STEP,
    ATTR_TARGET_KEY,
    ATTR_TARGET_TEMP_STEP,
    ATTR_TEMPERATURE_UNIT,
    ATTR_TIMER_ACTION,
    ATTR_TIMER_DEADLINE,
    ATTR_UNTIL_NEXT_BLOCK,
    CONF_LEGACY_OFF_TIME,
    CONF_LEGACY_ON_TIME,
    CONF_TARGETS,
    DEFAULT_PLAN_NAME,
    DOMAIN,
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
from .coordinator import RoomCoordinator
from .entity import room_device_info
from .models import (
    PlanConfig,
    TargetConfig,
    new_key,
    options_from_config,
    options_with_behavior,
    targets_as_data,
)
from .schedule import TargetController, async_resolve_schedule_entity_id

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one Scheduled Climate entity per target in the room."""
    coordinator: RoomCoordinator = hass.data[DOMAIN][entry.entry_id]
    registry = er.async_get(hass)

    entities: list[ScheduledClimateEntity] = []
    for controller in coordinator:
        target = controller.target
        wrapper_entity_id = registry.async_get_entity_id(
            CLIMATE_DOMAIN, DOMAIN, target.key
        )
        if wrapper_entity_id is not None and wrapper_entity_id == target.entity_id:
            target_object_id = target.entity_id.split(".", 1)[-1]
            registry.async_update_entity(
                wrapper_entity_id,
                new_entity_id=registry.async_generate_entity_id(
                    CLIMATE_DOMAIN,
                    f"{target_object_id}_scheduled",
                ),
            )
        entities.append(ScheduledClimateEntity(entry, coordinator, controller))

    async_add_entities(entities)
    _async_register_services()


@callback
def _async_register_services() -> None:
    """Register the entity services exposed by this platform."""
    platform = entity_platform.async_get_current_platform()
    timer_schema = {
        vol.Required(ATTR_DURATION): vol.All(
            cv.time_period,
            vol.Range(min=timedelta.resolution),
        )
    }
    platform.async_register_entity_service(
        SERVICE_START_ON_TIMER,
        timer_schema,
        "async_start_on_timer",
    )
    platform.async_register_entity_service(
        SERVICE_START_OFF_TIMER,
        timer_schema,
        "async_start_off_timer",
    )
    platform.async_register_entity_service(
        SERVICE_CANCEL_TIMER,
        None,
        "async_cancel_timer",
    )
    platform.async_register_entity_service(
        SERVICE_LINK_SCHEDULE,
        {
            vol.Optional(ATTR_SCHEDULE_ID): vol.Any(None, cv.string),
            vol.Optional(ATTR_PLAN): cv.string,
        },
        "async_link_schedule",
    )
    platform.async_register_entity_service(
        SERVICE_ENABLE_SCHEDULE,
        None,
        "async_enable_schedule",
    )
    platform.async_register_entity_service(
        SERVICE_DISABLE_SCHEDULE,
        None,
        "async_disable_schedule",
    )
    platform.async_register_entity_service(
        SERVICE_SET_OVERRIDE,
        {
            vol.Optional(ATTR_UNTIL_NEXT_BLOCK): cv.boolean,
            vol.Optional(ATTR_DURATION): vol.All(
                cv.time_period,
                vol.Range(min=timedelta.resolution),
            ),
            vol.Optional(ATTR_HVAC_MODE): vol.Coerce(HVACMode),
            vol.Optional(ATTR_TEMPERATURE): vol.Coerce(float),
            vol.Optional(ATTR_TARGET_TEMP_LOW): vol.Coerce(float),
            vol.Optional(ATTR_TARGET_TEMP_HIGH): vol.Coerce(float),
            vol.Optional(ATTR_FAN_MODE): cv.string,
            vol.Optional(ATTR_HUMIDITY): vol.Coerce(float),
        },
        "async_set_override",
    )
    platform.async_register_entity_service(
        SERVICE_CLEAR_OVERRIDE,
        None,
        "async_clear_override",
    )
    platform.async_register_entity_service(
        SERVICE_SELECT_PLAN,
        {vol.Required(ATTR_PLAN): cv.string},
        "async_select_plan",
    )


class ScheduledClimateEntity(ClimateEntity):
    """Mirror and control one existing climate entity in a room."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: RoomCoordinator,
        controller: TargetController,
    ) -> None:
        """Initialize the wrapper."""
        self._entry = entry
        self._coordinator = coordinator
        self._controller = controller
        self._attr_unique_id = controller.target.key
        self._attr_device_info = room_device_info(entry)
        # A room named after its only device should not repeat itself.
        self._attr_name = (
            None if controller.target.name == entry.title else controller.target.name
        )
        self._target_entity_id = controller.target.entity_id
        self._target_state: State | None = None
        self._unsub_target_registry: Callable[[], None] | None = None
        self._unsub_target_state: Callable[[], None] | None = None

    @property
    def suggested_object_id(self) -> str:
        """Return an entity ID suggestion distinct from the target."""
        target_object_id = self._target_entity_id.split(".", 1)[-1]
        return f"{target_object_id}_scheduled"

    async def async_added_to_hass(self) -> None:
        """Start tracking the target entity."""
        await super().async_added_to_hass()
        self._target_state = self.hass.states.get(self._target_entity_id)
        self._subscribe_target_registry()
        self._subscribe_target_state()
        self.async_on_remove(self._unsubscribe_target_registry)
        self.async_on_remove(self._unsubscribe_target_state)
        self.async_on_remove(
            self._controller.timer.async_add_listener(self._async_view_changed)
        )
        self.async_on_remove(
            self._controller.async_add_listener(self._async_view_changed)
        )
        self.async_on_remove(
            self._coordinator.async_add_listener(self._async_view_changed)
        )
        self._coordinator.async_register_entity(
            self._controller.target.key, self.entity_id
        )
        self.async_on_remove(
            lambda: self._coordinator.async_unregister_entity(
                self._controller.target.key
            )
        )

    @callback
    def _async_view_changed(self) -> None:
        """Write state after the schedule, plan or timer view changes."""
        self.async_write_ha_state()

    @callback
    def _subscribe_target_registry(self) -> None:
        """Subscribe to registry updates for the current target."""
        self._unsubscribe_target_registry()
        self._unsub_target_registry = async_track_entity_registry_updated_event(
            self.hass,
            [self._target_entity_id],
            self._async_target_registry_updated,
        )

    @callback
    def _unsubscribe_target_registry(self) -> None:
        """Unsubscribe from target registry updates."""
        if self._unsub_target_registry is not None:
            self._unsub_target_registry()
            self._unsub_target_registry = None

    @callback
    def _subscribe_target_state(self) -> None:
        """Subscribe to state updates for the current target."""
        self._unsubscribe_target_state()
        self._unsub_target_state = async_track_state_change_event(
            self.hass,
            [self._target_entity_id],
            self._async_target_state_changed,
        )

    @callback
    def _unsubscribe_target_state(self) -> None:
        """Unsubscribe from target state updates."""
        if self._unsub_target_state is not None:
            self._unsub_target_state()
            self._unsub_target_state = None

    @callback
    def _async_target_registry_updated(
        self, event: Event[EventEntityRegistryUpdatedData]
    ) -> None:
        """Follow the target when its entity ID changes."""
        if event.data["action"] != "update" or "old_entity_id" not in event.data:
            return

        self._target_entity_id = event.data["entity_id"]
        self._target_state = self.hass.states.get(self._target_entity_id)
        self._subscribe_target_registry()
        self._subscribe_target_state()
        self._controller.async_set_target_entity_id(self._target_entity_id)
        self._async_persist_target_entity_id()
        self.async_write_ha_state()

    @callback
    def _async_persist_target_entity_id(self) -> None:
        """Record the renamed target entity id in the config entry."""
        config = self._coordinator.config
        targets = [
            TargetConfig(
                key=target.key,
                entity_id=(
                    self._target_entity_id
                    if target.key == self._controller.target.key
                    else target.entity_id
                ),
                name=target.name,
            )
            for target in config.targets
        ]
        self.hass.config_entries.async_update_entry(
            self._entry,
            data={**self._entry.data, CONF_TARGETS: targets_as_data(targets)},
        )

    async def _async_target_state_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle a target state update."""
        self._target_state = event.data["new_state"]
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return whether the target is available."""
        return self._target_state is not None and self._target_state.state not in {
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        }

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return features supported by the target."""
        value = self._attribute("supported_features", 0)
        return ClimateEntityFeature(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return schedule, plan and hold diagnostics."""
        controller = self._controller
        coordinator = self._coordinator
        plans = coordinator.plans
        active_block = controller.active_block
        next_event = controller.next_event
        override = controller.override.state
        active_plan = plans.active_plan

        return {
            ATTR_TARGET_KEY: controller.target.key,
            ATTR_ROOM_ENTITIES: coordinator.async_room_entity_ids(),
            ATTR_SCHEDULE_ENABLED: controller.enabled,
            ATTR_SCHEDULE_ENTITY_ID: controller.schedule_entity_id,
            ATTR_SCHEDULE_ID: controller.schedule_id,
            ATTR_SCHEDULE_ACTIVE: active_block is not None,
            ATTR_ACTIVE_SCHEDULE_BLOCK: (
                active_block.as_dict() if active_block else None
            ),
            ATTR_NEXT_SCHEDULE_EVENT: next_event.isoformat() if next_event else None,
            ATTR_SCHEDULE_ISSUES: list(controller.issues),
            ATTR_LEGACY_SCHEDULE: coordinator.config.legacy_schedule,
            ATTR_PLAN_OPTIONS: list(coordinator.config.plan_names),
            ATTR_PLAN_SCHEDULES: coordinator.async_plan_schedule_ids(
                controller.target.key
            ),
            ATTR_ACTIVE_PLAN: active_plan.name if active_plan else None,
            ATTR_PLAN_SELECTION_MODE: coordinator.config.plan_selection.mode,
            ATTR_PLAN_RESOLVED_AUTOMATICALLY: (
                plans.automatic and plans.automatic_available
            ),
            ATTR_OVERRIDE_ACTIVE: override is not None,
            ATTR_OVERRIDE_UNTIL: override.until.isoformat() if override else None,
            ATTR_OVERRIDE_BLOCK: override.block.as_dict() if override else None,
            ATTR_TIMER_ACTION: controller.timer.action,
            ATTR_TIMER_DEADLINE: (
                controller.timer.deadline.isoformat()
                if controller.timer.deadline
                else None
            ),
        }

    # ------------------------------------------------------------------
    # Timer services
    # ------------------------------------------------------------------

    async def async_start_on_timer(self, duration: timedelta) -> None:
        """Start or replace a timer that turns the target on."""
        await self._controller.timer.async_start("on", duration)

    async def async_start_off_timer(self, duration: timedelta) -> None:
        """Start or replace a timer that turns the target off."""
        await self._controller.timer.async_start("off", duration)

    async def async_cancel_timer(self) -> None:
        """Cancel the active timer."""
        await self._controller.timer.async_cancel()

    # ------------------------------------------------------------------
    # Hold services
    # ------------------------------------------------------------------

    async def async_set_override(self, **values: Any) -> None:
        """Hold the target at requested settings for a while."""
        block = ScheduleBlock(
            hvac_mode=values.get(ATTR_HVAC_MODE),
            temperature=values.get(ATTR_TEMPERATURE),
            target_temp_low=values.get(ATTR_TARGET_TEMP_LOW),
            target_temp_high=values.get(ATTR_TARGET_TEMP_HIGH),
            fan_mode=values.get(ATTR_FAN_MODE),
            humidity=values.get(ATTR_HUMIDITY),
        )
        if block.is_empty:
            raise ServiceValidationError(
                "A hold needs at least one climate setting to apply"
            )

        await self._controller.async_set_override(
            block, self._override_deadline(values)
        )

    def _override_deadline(self, values: dict[str, Any]) -> datetime:
        """Return when a requested hold should lapse."""
        bounds = self._coordinator.config.override
        duration: timedelta | None = values.get(ATTR_DURATION)
        until_next_block = values.get(ATTR_UNTIL_NEXT_BLOCK)

        if duration is not None:
            minutes = bounds.clamp_minutes(duration.total_seconds() / 60)
            return dt_util.utcnow() + timedelta(minutes=minutes)

        now = dt_util.utcnow()
        if until_next_block is not False:
            next_event = self._controller.next_event
            if next_event is not None and next_event > now:
                return min(
                    dt_util.as_utc(next_event),
                    now + timedelta(minutes=bounds.max_minutes),
                )

        return now + timedelta(minutes=bounds.default_minutes)

    async def async_clear_override(self) -> None:
        """Drop the active hold and resume the schedule."""
        await self._controller.async_clear_override()

    # ------------------------------------------------------------------
    # Schedule and plan services
    # ------------------------------------------------------------------

    async def async_select_plan(self, plan: str) -> None:
        """Select the plan the whole room follows."""
        try:
            await self._coordinator.async_select_plan(plan)
        except ValueError as error:
            raise ServiceValidationError(str(error)) from error

    async def async_link_schedule(
        self, schedule_id: str | None = None, plan: str | None = None
    ) -> None:
        """Link, or unlink, a schedule helper for this target and plan."""
        config = self._coordinator.config
        key = self._controller.target.key
        target_plan = self._resolve_plan(plan)

        schedule_entity_id: str | None = None
        if schedule_id:
            schedule_entity_id = async_resolve_schedule_entity_id(
                self.hass, schedule_id
            )
            if schedule_entity_id is None:
                raise ServiceValidationError(
                    f"No schedule helper found for '{schedule_id}'"
                )

        updated = target_plan.with_schedule(key, schedule_entity_id)
        plans = list(config.plans)
        for index, existing in enumerate(plans):
            if existing.id == updated.id:
                plans[index] = updated
                break
        else:
            plans.append(updated)

        behaviors = dict(config.behaviors)
        if schedule_entity_id:
            behaviors[key] = replace(config.behavior_for(key), schedule_enabled=True)

        options = options_from_config(config, behaviors=behaviors, plans=plans)
        if schedule_entity_id:
            options.pop(CONF_LEGACY_ON_TIME, None)
            options.pop(CONF_LEGACY_OFF_TIME, None)

        self.hass.config_entries.async_update_entry(self._entry, options=options)

    def _resolve_plan(self, plan: str | None) -> PlanConfig:
        """Return the plan a link request targets, creating a default one."""
        config = self._coordinator.config
        if plan:
            resolved = config.plan_by_name(plan)
            if resolved is None:
                raise ServiceValidationError(f"Unknown plan '{plan}'")
            return resolved

        active = self._coordinator.plans.active_plan
        if active is not None:
            return active
        if config.plans:
            return config.plans[0]
        return PlanConfig(id=new_key(), name=DEFAULT_PLAN_NAME)

    async def async_enable_schedule(self) -> None:
        """Apply the active plan's schedule to this target again."""
        config = self._coordinator.config
        key = self._controller.target.key
        if self._coordinator.plans.schedule_entity_id(key) is None:
            raise ServiceValidationError(
                "Cannot enable the schedule: no schedule helper is linked"
            )
        self.hass.config_entries.async_update_entry(
            self._entry,
            options=options_with_behavior(
                config, key, replace(config.behavior_for(key), schedule_enabled=True)
            ),
        )

    async def async_disable_schedule(self) -> None:
        """Stop applying the schedule to this target without unlinking it."""
        config = self._coordinator.config
        key = self._controller.target.key
        self.hass.config_entries.async_update_entry(
            self._entry,
            options=options_with_behavior(
                config, key, replace(config.behavior_for(key), schedule_enabled=False)
            ),
        )

    # ------------------------------------------------------------------
    # Mirrored target state
    # ------------------------------------------------------------------

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current HVAC mode."""
        if not self.available:
            return None
        try:
            return HVACMode(self._target_state.state)
        except ValueError:
            return None

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return available HVAC modes."""
        return [HVACMode(mode) for mode in self._attribute(ATTR_HVAC_MODES, [])]

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action."""
        action = self._attribute(ATTR_HVAC_ACTION)
        return HVACAction(action) if action else None

    @property
    def temperature_unit(self) -> str:
        """Return the target temperature unit."""
        return self._attribute(
            ATTR_TEMPERATURE_UNIT, self.hass.config.units.temperature_unit
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._attribute(ATTR_CURRENT_TEMPERATURE)

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._attribute(ATTR_TEMPERATURE)

    @property
    def target_temperature_high(self) -> float | None:
        """Return the high target temperature."""
        return self._attribute(ATTR_TARGET_TEMP_HIGH)

    @property
    def target_temperature_low(self) -> float | None:
        """Return the low target temperature."""
        return self._attribute(ATTR_TARGET_TEMP_LOW)

    @property
    def min_temp(self) -> float:
        """Return the minimum target temperature."""
        return self._attribute(ATTR_MIN_TEMP, super().min_temp)

    @property
    def max_temp(self) -> float:
        """Return the maximum target temperature."""
        return self._attribute(ATTR_MAX_TEMP, super().max_temp)

    @property
    def target_temperature_step(self) -> float | None:
        """Return the target temperature step."""
        return self._attribute(ATTR_TARGET_TEMP_STEP)

    @property
    def current_humidity(self) -> float | None:
        """Return current humidity."""
        return self._attribute(ATTR_CURRENT_HUMIDITY)

    @property
    def target_humidity(self) -> float | None:
        """Return target humidity."""
        return self._attribute(ATTR_HUMIDITY)

    @property
    def min_humidity(self) -> float:
        """Return the minimum target humidity."""
        return self._attribute(ATTR_MIN_HUMIDITY, super().min_humidity)

    @property
    def max_humidity(self) -> float:
        """Return the maximum target humidity."""
        return self._attribute(ATTR_MAX_HUMIDITY, super().max_humidity)

    @property
    def target_humidity_step(self) -> int | None:
        """Return the target humidity step."""
        return self._attribute(ATTR_TARGET_HUMIDITY_STEP)

    @property
    def fan_mode(self) -> str | None:
        """Return the current fan mode."""
        return self._attribute(ATTR_FAN_MODE)

    @property
    def fan_modes(self) -> list[str] | None:
        """Return available fan modes."""
        return self._attribute(ATTR_FAN_MODES)

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return self._attribute(ATTR_PRESET_MODE)

    @property
    def preset_modes(self) -> list[str] | None:
        """Return available preset modes."""
        return self._attribute(ATTR_PRESET_MODES)

    @property
    def swing_mode(self) -> str | None:
        """Return the current swing mode."""
        return self._attribute(ATTR_SWING_MODE)

    @property
    def swing_modes(self) -> list[str] | None:
        """Return available swing modes."""
        return self._attribute(ATTR_SWING_MODES)

    @property
    def swing_horizontal_mode(self) -> str | None:
        """Return the current horizontal swing mode."""
        return self._attribute(ATTR_SWING_HORIZONTAL_MODE)

    @property
    def swing_horizontal_modes(self) -> list[str] | None:
        """Return available horizontal swing modes."""
        return self._attribute(ATTR_SWING_HORIZONTAL_MODES)

    def _attribute(self, name: str, default: Any = None) -> Any:
        """Return an attribute from the target state."""
        if self._target_state is None:
            return default
        return self._target_state.attributes.get(name, default)

    async def _async_forward(self, service: str, data: dict[str, Any]) -> None:
        """Forward a climate service call to the target entity."""
        if self.entity_id == self._target_entity_id:
            raise ServiceValidationError(
                "Scheduled Climate cannot use itself as its target entity"
            )
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            service,
            {**data, ATTR_ENTITY_ID: self._target_entity_id},
            blocking=True,
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        await self._async_forward(SERVICE_SET_TEMPERATURE, kwargs)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the target HVAC mode."""
        await self._async_forward(SERVICE_SET_HVAC_MODE, {ATTR_HVAC_MODE: hvac_mode})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the target fan mode."""
        await self._async_forward(SERVICE_SET_FAN_MODE, {ATTR_FAN_MODE: fan_mode})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the target preset mode."""
        await self._async_forward(
            SERVICE_SET_PRESET_MODE, {ATTR_PRESET_MODE: preset_mode}
        )

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set the target swing mode."""
        await self._async_forward(SERVICE_SET_SWING_MODE, {ATTR_SWING_MODE: swing_mode})

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        """Set the target horizontal swing mode."""
        await self._async_forward(
            SERVICE_SET_SWING_HORIZONTAL_MODE,
            {ATTR_SWING_HORIZONTAL_MODE: swing_horizontal_mode},
        )

    async def async_set_humidity(self, humidity: int) -> None:
        """Set the target humidity."""
        await self._async_forward(SERVICE_SET_HUMIDITY, {ATTR_HUMIDITY: humidity})

    async def async_turn_on(self) -> None:
        """Turn on the target."""
        await self._async_forward(SERVICE_TURN_ON, {})

    async def async_turn_off(self) -> None:
        """Turn off the target."""
        await self._async_forward(SERVICE_TURN_OFF, {})
