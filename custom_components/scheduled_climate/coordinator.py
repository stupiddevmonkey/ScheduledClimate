"""Room coordinator for Scheduled Climate.

One coordinator per config entry. It owns the plan selector and one
:class:`TargetController` per climate entity in the room, and re-points every
controller at a new schedule helper whenever the active plan changes.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .models import RoomConfig, TargetConfig
from .plan import PlanSelector
from .schedule import TARGET_ISSUES, TargetController

_LOGGER = logging.getLogger(__name__)


class RoomCoordinator:
    """Own every runtime object behind one Scheduled Climate config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.config = RoomConfig.from_entry(entry)
        self.plans = PlanSelector(hass, entry, self.config)
        self.controllers: dict[str, TargetController] = {
            target.key: TargetController(hass, entry, target, self.config)
            for target in self.config.targets
        }
        self._listeners: list[Callable[[], None]] = []
        self._entity_ids: dict[str, str] = {}
        self._unsub_plans: Callable[[], None] | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_initialize(self) -> None:
        """Resolve the active plan and start every target controller."""
        self._async_clear_legacy_issues()
        await self.plans.async_initialize()
        self._unsub_plans = self.plans.async_add_listener(self._async_plan_changed)
        for key, controller in self.controllers.items():
            await controller.async_initialize(self.plans.schedule_entity_id(key))

    @callback
    def async_shutdown(self) -> None:
        """Stop every runtime object owned by this entry."""
        if self._unsub_plans is not None:
            self._unsub_plans()
            self._unsub_plans = None
        for controller in self.controllers.values():
            controller.async_shutdown()
        self.plans.async_shutdown()
        self._listeners.clear()

    @callback
    def _async_clear_legacy_issues(self) -> None:
        """Drop repair issues raised by the pre-room, per-entry id scheme."""
        for issue in TARGET_ISSUES:
            ir.async_delete_issue(self.hass, DOMAIN, f"{issue}_{self.entry.entry_id}")

    # ------------------------------------------------------------------
    # Plan changes
    # ------------------------------------------------------------------

    @callback
    def _async_plan_changed(self) -> None:
        """Re-point every controller after the active plan changed."""
        self.hass.async_create_task(self._async_apply_active_plan())

    async def _async_apply_active_plan(self) -> None:
        """Hand each controller the schedule helper for the active plan."""
        for key, controller in self.controllers.items():
            await controller.async_update_config(
                self.config, self.plans.schedule_entity_id(key)
            )
        self.async_notify()

    async def async_select_plan(self, option: str) -> None:
        """Select a plan by name, or hand control to the outdoor sensor."""
        await self.plans.async_select(option)

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a callback fired when the room view changes."""
        self._listeners.append(listener)

        @callback
        def remove_listener() -> None:
            """Remove the registered callback."""
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    @callback
    def async_notify(self) -> None:
        """Notify registered listeners that the room view changed."""
        for listener in list(self._listeners):
            listener()

    # ------------------------------------------------------------------
    # Views used by entities, services and diagnostics
    # ------------------------------------------------------------------

    @property
    def targets(self) -> tuple[TargetConfig, ...]:
        """Return the targets configured for this room."""
        return self.config.targets

    def __iter__(self) -> Iterator[TargetController]:
        """Iterate over the controllers in configured target order."""
        return iter(self.controllers.values())

    def controller_for(self, target_key: str) -> TargetController | None:
        """Return the controller for one target."""
        return self.controllers.get(target_key)

    def controller_for_entity(self, entity_id: str) -> TargetController | None:
        """Return the controller wrapping one climate entity."""
        return next(
            (
                controller
                for controller in self.controllers.values()
                if controller.target_entity_id == entity_id
            ),
            None,
        )

    @callback
    def async_register_entity(self, target_key: str, entity_id: str) -> None:
        """Record a wrapper entity id and refresh the room view.

        Entities are added one at a time, so every entity already present is
        told to rewrite its state once the last one arrives. Without this the
        first entity would advertise an incomplete room.
        """
        if self._entity_ids.get(target_key) == entity_id:
            return
        self._entity_ids[target_key] = entity_id
        self.async_notify()

    @callback
    def async_unregister_entity(self, target_key: str) -> None:
        """Forget a wrapper entity that is going away."""
        self._entity_ids.pop(target_key, None)

    @callback
    def async_room_entity_ids(self) -> list[str]:
        """Return this room's wrapper climate entity ids, in target order."""
        return [
            self._entity_ids[target.key]
            for target in self.config.targets
            if target.key in self._entity_ids
        ]

    @callback
    def async_plan_schedule_ids(self, target_key: str) -> dict[str, str | None]:
        """Return each plan's schedule helper storage id for one target.

        The dashboard card needs this to edit a plan that is not the active
        one, because a schedule helper is addressed by storage id rather than
        by entity id over the websocket API.
        """
        registry = er.async_get(self.hass)
        schedule_ids: dict[str, str | None] = {}
        for plan in self.config.plans:
            entity_id = plan.schedule_for(target_key)
            entry = registry.async_get(entity_id) if entity_id else None
            schedule_ids[plan.name] = entry.unique_id if entry else None
        return schedule_ids
