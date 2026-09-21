"""Diagnostics support for Scheduled Climate.

A config entry now describes a whole room, so diagnostics report the plan
selector plus every target controller the :class:`RoomCoordinator` owns. None
of this data is secret, so nothing is redacted.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import RoomCoordinator
from .schedule import TargetController


def _plan_diagnostics(coordinator: RoomCoordinator) -> dict[str, Any]:
    """Return the room's plan selection state."""
    plans = coordinator.plans
    selection = coordinator.config.plan_selection
    active_plan = plans.active_plan
    return {
        "mode": selection.mode,
        "automatic": plans.automatic,
        "automatic_available": plans.automatic_available,
        "active_plan": active_plan.name if active_plan else None,
        "options": list(plans.options),
        "outdoor_temp_entity_id": selection.outdoor_temp_entity_id,
        "outdoor_temperature": plans.outdoor_temperature,
        "hysteresis": selection.hysteresis,
        "sustain_minutes": selection.sustain_minutes,
        "plans": [
            {
                "id": plan.id,
                "name": plan.name,
                "min_outdoor_temp": plan.min_outdoor_temp,
                "schedules": dict(plan.schedules),
            }
            for plan in coordinator.config.plans
        ],
    }


def _target_diagnostics(
    hass: HomeAssistant, controller: TargetController
) -> dict[str, Any]:
    """Return the runtime state of one target controller."""
    active_block = controller.active_block
    next_event = controller.next_event
    override_state = controller.override.state
    timer = controller.timer
    target_state = hass.states.get(controller.target_entity_id)
    return {
        "key": controller.target.key,
        "name": controller.target.name,
        "entity_id": controller.target_entity_id,
        "behavior": controller.behavior.as_dict(),
        "schedule": {
            "entity_id": controller.schedule_entity_id,
            "schedule_id": controller.schedule_id,
            "enabled": controller.enabled,
            "state": (
                controller.schedule_state.state if controller.schedule_state else None
            ),
            "active_block": active_block.as_dict() if active_block else None,
            "next_event": next_event.isoformat() if next_event else None,
            "issues": list(controller.issues),
        },
        "override": override_state.as_dict() if override_state else None,
        "timer": {
            "action": timer.action,
            "deadline": timer.deadline.isoformat() if timer.deadline else None,
        },
        "state": target_state.state if target_state else None,
        "attributes": dict(target_state.attributes) if target_state else None,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a room config entry."""
    coordinator: RoomCoordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry": {
            "version": entry.version,
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "plan": _plan_diagnostics(coordinator),
        "targets": [
            _target_diagnostics(hass, controller) for controller in coordinator
        ],
    }
