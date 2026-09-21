"""Per-target schedule control for Scheduled Climate.

One :class:`TargetController` owns a single climate entity in a room: the
schedule helper it currently follows (which changes when the active plan
changes), its one-shot timer, and its temporary override.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypedDict

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    SERVICE_SET_HVAC_MODE,
    HVACMode,
)
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.schedule import ATTR_NEXT_EVENT
from homeassistant.components.schedule import DOMAIN as SCHEDULE_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store

from .block import ScheduleBlock, build_plan
from .const import (
    DOMAIN,
    ISSUE_BLOCK_UNSUPPORTED,
    ISSUE_SCHEDULE_MISSING,
    ISSUE_SCHEDULE_NOT_LINKED,
    OFF_BEHAVIOR_IGNORE,
)
from .models import RoomConfig, TargetBehavior, TargetConfig
from .override import OverrideManager, OverrideState
from .timer import TimerManager

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "scheduled_climate"
STORAGE_LAST_ACTIVE_HVAC_MODE = "last_active_hvac_mode"

UNUSABLE_STATES = frozenset({STATE_UNAVAILABLE, STATE_UNKNOWN})

TARGET_ISSUES = (
    ISSUE_SCHEDULE_MISSING,
    ISSUE_SCHEDULE_NOT_LINKED,
    ISSUE_BLOCK_UNSUPPORTED,
)


class ScheduleStorageData(TypedDict, total=False):
    """Stored schedule runtime state."""

    last_active_hvac_mode: str


class _Unset:
    """Sentinel for a block that has not been observed yet."""


_UNSET = _Unset()

AppliedBlock = ScheduleBlock | None | _Unset


class TargetController:
    """Apply the active plan's schedule helper to one climate entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        target: TargetConfig,
        config: RoomConfig,
    ) -> None:
        """Initialize the controller for one target."""
        self.hass = hass
        self.entry = entry
        self.target = target
        self._config = config
        self._schedule_entity_id: str | None = None
        self._unsubscribers: list[Callable[[], None]] = []
        self._listeners: list[Callable[[], None]] = []
        self._last_active_hvac_mode: HVACMode | None = None
        self._last_applied: AppliedBlock = _UNSET
        self._pending: AppliedBlock = _UNSET
        self._issues: tuple[str, ...] = ()
        self._store = Store[ScheduleStorageData](
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}.{target.key}",
        )
        self.timer = TimerManager(
            hass,
            target.key,
            self.async_handle_on,
            self.async_handle_off,
        )
        self.override = OverrideManager(
            hass,
            target.key,
            self._async_override_expired,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_initialize(self, schedule_entity_id: str | None) -> None:
        """Restore runtime state and start following a schedule helper."""
        stored = await self._store.async_load()
        if stored and (mode := stored.get(STORAGE_LAST_ACTIVE_HVAC_MODE)):
            try:
                restored_mode = HVACMode(mode)
            except ValueError:
                restored_mode = None
            if restored_mode is not HVACMode.OFF:
                self._last_active_hvac_mode = restored_mode

        self._schedule_entity_id = schedule_entity_id
        self.async_setup()

        await self.override.async_initialize()

        if self.override.active:
            await self._async_apply_override()
            self._last_applied = self.active_block
        elif self.enabled and self.apply_on_start:
            await self._async_handle_block(self.active_block)
        else:
            self._last_applied = self.active_block

        self._async_update_issues()
        await self.timer.async_initialize()

    @callback
    def async_setup(self) -> None:
        """Track the current schedule helper and the target availability."""
        self._cancel_schedule_callbacks()
        self._unsubscribers.append(
            async_track_state_change_event(
                self.hass, [self.target.entity_id], self._async_target_changed
            )
        )
        if self._schedule_entity_id is None:
            return

        self._unsubscribers.append(
            async_track_state_change_event(
                self.hass, [self._schedule_entity_id], self._async_schedule_changed
            )
        )

    @callback
    def async_shutdown(self) -> None:
        """Cancel all registered runtime callbacks."""
        self._cancel_schedule_callbacks()
        self._listeners.clear()
        for issue in TARGET_ISSUES:
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_id(issue))
        self.timer.async_shutdown()
        self.override.async_shutdown()

    @callback
    def _cancel_schedule_callbacks(self) -> None:
        """Cancel registered state callbacks."""
        while self._unsubscribers:
            self._unsubscribers.pop()()

    async def async_update_config(
        self, config: RoomConfig, schedule_entity_id: str | None
    ) -> None:
        """Adopt a new room configuration and possibly a new schedule helper."""
        self._config = config
        target = config.target_by_key(self.target.key)
        entity_changed = (
            target is not None and target.entity_id != self.target.entity_id
        )
        if target is not None:
            self.target = target

        if entity_changed or schedule_entity_id != self._schedule_entity_id:
            self._schedule_entity_id = schedule_entity_id
            self._last_applied = _UNSET
            self._pending = _UNSET
            self.async_setup()

        if not self.override.active and self.enabled:
            await self._async_handle_block(self.active_block)
        self._async_update_issues()
        self._notify_listeners()

    @callback
    def async_set_target_entity_id(self, entity_id: str) -> None:
        """Follow the target after Home Assistant renames its entity id."""
        if entity_id == self.target.entity_id:
            return
        self.target = TargetConfig(
            key=self.target.key, entity_id=entity_id, name=self.target.name
        )
        self.async_setup()

    # ------------------------------------------------------------------
    # Configuration views
    # ------------------------------------------------------------------

    @property
    def behavior(self) -> TargetBehavior:
        """Return the configured behaviour for this target."""
        return self._config.behavior_for(self.target.key)

    @property
    def target_entity_id(self) -> str:
        """Return the wrapped climate entity id."""
        return self.target.entity_id

    @property
    def schedule_entity_id(self) -> str | None:
        """Return the schedule helper entity id currently followed."""
        return self._schedule_entity_id

    @property
    def enabled(self) -> bool:
        """Return whether the schedule is applied to the target."""
        if self._schedule_entity_id is None:
            return False
        return self.behavior.schedule_enabled

    @property
    def off_behavior(self) -> str:
        """Return what happens when no schedule block is active."""
        return self.behavior.off_behavior

    @property
    def apply_on_start(self) -> bool:
        """Return whether the active block is applied during setup."""
        return self.behavior.apply_on_start

    @property
    def issues(self) -> tuple[str, ...]:
        """Return the problems found while applying the last block."""
        return self._issues

    @property
    def schedule_state(self) -> State | None:
        """Return the followed schedule helper state."""
        entity_id = self._schedule_entity_id
        return self.hass.states.get(entity_id) if entity_id else None

    @property
    def active_block(self) -> ScheduleBlock | None:
        """Return the currently active schedule block."""
        return ScheduleBlock.from_state(self.schedule_state)

    @property
    def next_event(self) -> datetime | None:
        """Return the next schedule boundary reported by the helper."""
        state = self.schedule_state
        if state is None:
            return None
        value = state.attributes.get(ATTR_NEXT_EVENT)
        return value if isinstance(value, datetime) else None

    @property
    def schedule_id(self) -> str | None:
        """Return the storage collection id of the followed schedule helper."""
        entity_id = self._schedule_entity_id
        if entity_id is None:
            return None
        registry_entry = er.async_get(self.hass).async_get(entity_id)
        return registry_entry.unique_id if registry_entry else None

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a callback fired when the schedule view changes."""
        self._listeners.append(listener)

        @callback
        def remove_listener() -> None:
            """Remove the registered callback."""
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    @callback
    def _notify_listeners(self) -> None:
        """Notify registered listeners that the schedule view changed."""
        for listener in list(self._listeners):
            listener()

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    async def async_set_override(self, block: ScheduleBlock, until: datetime) -> None:
        """Hold the target at a requested block until a deadline."""
        await self.override.async_set(block, until)
        await self._async_apply_override()
        self._notify_listeners()

    async def async_clear_override(self) -> None:
        """Drop the active hold and resume the schedule immediately."""
        if not self.override.active:
            return
        await self.override.async_clear()
        await self._async_resume_schedule()
        self._notify_listeners()

    async def _async_override_expired(self, _now: datetime) -> None:
        """Resume the schedule once a hold runs out."""
        await self._async_resume_schedule()
        self._notify_listeners()

    async def _async_apply_override(self) -> None:
        """Push the held block to the target."""
        state = self.override.state
        if state is None:
            return
        await self._async_apply(state.block)

    async def _async_resume_schedule(self) -> None:
        """Re-apply whatever the schedule asks for right now."""
        if not self.enabled:
            return
        self._last_applied = _UNSET
        await self._async_handle_block(self.active_block)

    # ------------------------------------------------------------------
    # Schedule application
    # ------------------------------------------------------------------

    async def _async_schedule_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Apply the schedule helper state to the target."""
        await self._async_handle_block(
            ScheduleBlock.from_state(event.data["new_state"])
        )
        self._async_update_issues()
        self._notify_listeners()

    async def _async_target_changed(self, event: Event[EventStateChangedData]) -> None:
        """Apply a deferred block once the target becomes usable again."""
        if isinstance(self._pending, _Unset):
            return
        new_state = event.data["new_state"]
        if new_state is None or new_state.state in UNUSABLE_STATES:
            return

        pending = self._pending
        self._pending = _UNSET
        await self._async_apply(pending)

    async def _async_handle_block(self, block: ScheduleBlock | None) -> None:
        """Apply a block when it differs from the last applied one."""
        if not self.enabled:
            return
        if self.override.active:
            # A hold suppresses the schedule, but the block is still recorded
            # so the right one is applied the moment the hold ends.
            self._last_applied = block
            return
        if not isinstance(self._last_applied, _Unset) and block == self._last_applied:
            return

        self._last_applied = block
        await self._async_apply(block)

    async def _async_apply(self, block: ScheduleBlock | None) -> None:
        """Send the climate commands for a block to the target entity."""
        state = self.hass.states.get(self.target.entity_id)
        if state is None or state.state in UNUSABLE_STATES:
            _LOGGER.debug(
                "Deferring the schedule block for %s until it is available",
                self.target.entity_id,
            )
            self._pending = block
            return

        if block is None:
            self._issues = ()
            await self._async_apply_off(state)
            return

        plan = build_plan(block, state, self._fallback_modes())
        self._issues = plan.issues
        if plan.issues:
            _LOGGER.warning(
                "The schedule block for %s could not be fully applied: %s",
                self.target.entity_id,
                "; ".join(plan.issues),
            )

        for command in plan.commands:
            await self._async_call(command.service, command.data)

        requested_mode = next(
            (
                command.data[ATTR_HVAC_MODE]
                for command in plan.commands
                if command.service == SERVICE_SET_HVAC_MODE
            ),
            None,
        )
        if requested_mode is not None and requested_mode != HVACMode.OFF:
            await self._async_store_active_mode(HVACMode(requested_mode))

    async def _async_apply_off(self, state: State) -> None:
        """Turn the target off when no schedule block is active."""
        if self.off_behavior == OFF_BEHAVIOR_IGNORE:
            return
        await self.async_handle_off_state(state)

    async def async_handle_on(self, _now: datetime) -> None:
        """Turn the target on, used by the manual timer."""
        await self._async_clear_override_for_timer()
        state = self.hass.states.get(self.target.entity_id)
        if state is None or state.state in UNUSABLE_STATES:
            return

        plan = build_plan(ScheduleBlock(), state, self._fallback_modes())
        for command in plan.commands:
            await self._async_call(command.service, command.data)

    async def async_handle_off(self, _now: datetime) -> None:
        """Turn the target off, used by the manual timer."""
        await self._async_clear_override_for_timer()
        state = self.hass.states.get(self.target.entity_id)
        if state is None or state.state in UNUSABLE_STATES:
            return
        await self.async_handle_off_state(state)

    async def _async_clear_override_for_timer(self) -> None:
        """Drop a hold when a timer fires; the timer is the newer intent."""
        if self.override.active:
            await self.override.async_clear()
            self._last_applied = _UNSET
            self._notify_listeners()

    async def async_handle_off_state(self, state: State) -> None:
        """Remember the active mode and turn the target off."""
        await self._async_remember_active_mode(state)
        if HVACMode.OFF in (state.attributes.get(ATTR_HVAC_MODES) or []):
            await self._async_call(
                SERVICE_SET_HVAC_MODE, {ATTR_HVAC_MODE: HVACMode.OFF}
            )

    def _fallback_modes(self) -> tuple[str, ...]:
        """Return the preferred HVAC modes when a block does not specify one."""
        candidates = (self._last_active_hvac_mode, self.behavior.default_hvac_mode)
        return tuple(str(mode) for mode in candidates if mode is not None)

    async def _async_remember_active_mode(self, state: State) -> None:
        """Store the current HVAC mode so it can be restored later."""
        try:
            current_mode = HVACMode(state.state)
        except ValueError:
            return
        if current_mode is not HVACMode.OFF:
            await self._async_store_active_mode(current_mode)

    async def _async_store_active_mode(self, mode: HVACMode) -> None:
        """Persist the last known active HVAC mode."""
        if mode is self._last_active_hvac_mode:
            return
        self._last_active_hvac_mode = mode
        await self._store.async_save({STORAGE_LAST_ACTIVE_HVAC_MODE: mode.value})

    async def _async_call(self, service: str, data: dict[str, Any]) -> None:
        """Call a climate service on the target entity."""
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            service,
            {ATTR_ENTITY_ID: self.target.entity_id, **data},
            blocking=True,
        )

    # ------------------------------------------------------------------
    # Repairs
    # ------------------------------------------------------------------

    def _issue_id(self, issue: str) -> str:
        """Return the repair issue id for this target."""
        return f"{issue}_{self.entry.entry_id}_{self.target.key}"

    @callback
    def _async_update_issues(self) -> None:
        """Create or resolve repair issues for the current configuration."""
        placeholders = {"name": self.target.name}

        self._async_set_issue(
            ISSUE_SCHEDULE_NOT_LINKED,
            self._schedule_entity_id is None
            and self._config.legacy_schedule is not None,
            placeholders,
        )
        self._async_set_issue(
            ISSUE_SCHEDULE_MISSING,
            self._schedule_entity_id is not None and self.schedule_state is None,
            {**placeholders, "entity_id": self._schedule_entity_id or ""},
        )
        self._async_set_issue(
            ISSUE_BLOCK_UNSUPPORTED,
            bool(self._issues),
            {**placeholders, "issues": "; ".join(self._issues)},
        )

    @callback
    def _async_set_issue(
        self, issue: str, active: bool, placeholders: dict[str, str]
    ) -> None:
        """Create or delete one repair issue."""
        issue_id = self._issue_id(issue)
        if not active:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return

        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=issue,
            translation_placeholders=placeholders,
        )


@callback
def async_resolve_schedule_entity_id(
    hass: HomeAssistant, schedule_id: str
) -> str | None:
    """Return the entity id for a schedule helper storage collection id."""
    return er.async_get(hass).async_get_entity_id(
        SCHEDULE_DOMAIN, SCHEDULE_DOMAIN, schedule_id
    )


__all__ = [
    "OverrideState",
    "TargetController",
    "async_resolve_schedule_entity_id",
]
