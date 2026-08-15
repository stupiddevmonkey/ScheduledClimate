"""Scheduled Climate wrapper entity."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
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

from .const import (
    ATTR_ACTIVE_SCHEDULE_BLOCK,
    ATTR_DURATION,
    ATTR_LEGACY_SCHEDULE,
    ATTR_MAX_HUMIDITY,
    ATTR_MAX_TEMP,
    ATTR_MIN_HUMIDITY,
    ATTR_MIN_TEMP,
    ATTR_NEXT_SCHEDULE_EVENT,
    ATTR_SCHEDULE_ACTIVE,
    ATTR_SCHEDULE_ENABLED,
    ATTR_SCHEDULE_ENTITY_ID,
    ATTR_SCHEDULE_ID,
    ATTR_SCHEDULE_ISSUES,
    ATTR_TARGET_HUMIDITY_STEP,
    ATTR_TARGET_TEMP_STEP,
    ATTR_TEMPERATURE_UNIT,
    ATTR_TIMER_ACTION,
    ATTR_TIMER_DEADLINE,
    CONF_LEGACY_OFF_TIME,
    CONF_LEGACY_ON_TIME,
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
from .schedule import ScheduleManager, async_resolve_schedule_entity_id

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a Scheduled Climate entity."""
    manager: ScheduleManager = hass.data[DOMAIN][entry.entry_id]
    target_entity_id: str = entry.data[CONF_TARGET_ENTITY_ID]
    registry = er.async_get(hass)
    wrapper_entity_id = registry.async_get_entity_id(
        CLIMATE_DOMAIN, DOMAIN, entry.entry_id
    )
    if wrapper_entity_id is not None and wrapper_entity_id == target_entity_id:
        target_object_id = target_entity_id.split(".", 1)[-1]
        registry.async_update_entity(
            wrapper_entity_id,
            new_entity_id=registry.async_generate_entity_id(
                CLIMATE_DOMAIN,
                f"{target_object_id}_scheduled",
            ),
        )
    async_add_entities(
        [
            ScheduledClimateEntity(
                entry.entry_id,
                entry.title,
                target_entity_id,
                manager,
            )
        ]
    )
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
        {vol.Optional(ATTR_SCHEDULE_ID): vol.Any(None, cv.string)},
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


class ScheduledClimateEntity(ClimateEntity):
    """Mirror and control an existing climate entity."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = None

    def __init__(
        self,
        entry_id: str,
        name: str,
        target_entity_id: str,
        schedule_manager: ScheduleManager,
    ) -> None:
        """Initialize the wrapper."""
        self._attr_unique_id = entry_id
        self._attr_device_info = {
            "identifiers": {("scheduled_climate", entry_id)},
            "name": name,
        }
        self._target_entity_id = target_entity_id
        self._schedule_manager = schedule_manager
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
            self._schedule_manager.timer.async_add_listener(
                self._async_manager_state_changed
            )
        )
        self.async_on_remove(
            self._schedule_manager.async_add_listener(self._async_manager_state_changed)
        )

    @callback
    def _async_manager_state_changed(self) -> None:
        """Write state after the schedule or timer view changes."""
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

        if entry := self.hass.config_entries.async_get_entry(self._attr_unique_id):
            self.hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, CONF_TARGET_ENTITY_ID: self._target_entity_id},
            )

        self.async_write_ha_state()

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
        """Return schedule diagnostics."""
        manager = self._schedule_manager
        active_block = manager.active_block
        next_event = manager.next_event
        return {
            ATTR_SCHEDULE_ENABLED: manager.enabled,
            ATTR_SCHEDULE_ENTITY_ID: manager.schedule_entity_id,
            ATTR_SCHEDULE_ID: manager.schedule_id,
            ATTR_SCHEDULE_ACTIVE: active_block is not None,
            ATTR_ACTIVE_SCHEDULE_BLOCK: (
                active_block.as_dict() if active_block else None
            ),
            ATTR_NEXT_SCHEDULE_EVENT: next_event.isoformat() if next_event else None,
            ATTR_SCHEDULE_ISSUES: list(manager.issues),
            ATTR_LEGACY_SCHEDULE: manager.legacy_schedule,
            ATTR_TIMER_ACTION: manager.timer.action,
            ATTR_TIMER_DEADLINE: (
                manager.timer.deadline.isoformat() if manager.timer.deadline else None
            ),
        }

    async def async_start_on_timer(self, duration: timedelta) -> None:
        """Start or replace a timer that turns the target on."""
        await self._schedule_manager.timer.async_start("on", duration)

    async def async_start_off_timer(self, duration: timedelta) -> None:
        """Start or replace a timer that turns the target off."""
        await self._schedule_manager.timer.async_start("off", duration)

    async def async_cancel_timer(self) -> None:
        """Cancel the active timer."""
        await self._schedule_manager.timer.async_cancel()

    async def async_link_schedule(self, schedule_id: str | None = None) -> None:
        """Link, or unlink, the schedule helper that drives this entity."""
        entry = self.hass.config_entries.async_get_entry(self._attr_unique_id)
        if entry is None:
            raise ServiceValidationError("Config entry is no longer available")

        options = dict(entry.options)
        if schedule_id:
            schedule_entity_id = async_resolve_schedule_entity_id(
                self.hass, schedule_id
            )
            if schedule_entity_id is None:
                raise ServiceValidationError(
                    f"No schedule helper found for '{schedule_id}'"
                )
            options[CONF_SCHEDULE_ENTITY_ID] = schedule_entity_id
            options[CONF_SCHEDULE_ENABLED] = True
            options.pop(CONF_LEGACY_ON_TIME, None)
            options.pop(CONF_LEGACY_OFF_TIME, None)
        else:
            options.pop(CONF_SCHEDULE_ENTITY_ID, None)
            options[CONF_SCHEDULE_ENABLED] = False

        self.hass.config_entries.async_update_entry(entry, options=options)

    async def async_enable_schedule(self) -> None:
        """Enable the linked schedule without changing which schedule is linked."""
        entry = self.hass.config_entries.async_get_entry(self._attr_unique_id)
        if entry is None:
            raise ServiceValidationError("Config entry is no longer available")
        if not entry.options.get(CONF_SCHEDULE_ENTITY_ID):
            raise ServiceValidationError(
                "Cannot enable the schedule: no schedule helper is linked"
            )
        self.hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_SCHEDULE_ENABLED: True}
        )

    async def async_disable_schedule(self) -> None:
        """Disable the linked schedule without unlinking it."""
        entry = self.hass.config_entries.async_get_entry(self._attr_unique_id)
        if entry is None:
            raise ServiceValidationError("Config entry is no longer available")
        self.hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_SCHEDULE_ENABLED: False}
        )

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
