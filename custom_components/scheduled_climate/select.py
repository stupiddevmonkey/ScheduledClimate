"""Active plan selection entity for Scheduled Climate."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory

from .const import (
    ATTR_OUTDOOR_TEMPERATURE,
    ATTR_PLAN_RESOLVED_AUTOMATICALLY,
    ATTR_PLAN_SELECTION_MODE,
    DOMAIN,
)
from .coordinator import RoomCoordinator
from .entity import room_device_info

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the active plan selector for a room."""
    coordinator: RoomCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SchedulePlanSelect(entry, coordinator)])


class SchedulePlanSelect(SelectEntity):
    """Expose which schedule plan the room is following."""

    _attr_has_entity_name = True
    _attr_translation_key = "schedule_plan"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:calendar-sync"

    def __init__(self, entry: ConfigEntry, coordinator: RoomCoordinator) -> None:
        """Initialize the plan selector entity."""
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_plan"
        self._attr_device_info = room_device_info(entry)

    async def async_added_to_hass(self) -> None:
        """Follow plan changes coming from the coordinator."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._coordinator.plans.async_add_listener(self._async_plan_changed)
        )
        self.async_on_remove(
            self._coordinator.async_add_listener(self._async_plan_changed)
        )

    @callback
    def _async_plan_changed(self) -> None:
        """Write state after the active plan changed."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return whether any plan is configured."""
        return bool(self._coordinator.plans.options)

    @property
    def options(self) -> list[str]:
        """Return the selectable plans, plus Automatic when it is usable."""
        return self._coordinator.plans.options

    @property
    def current_option(self) -> str | None:
        """Return the plan currently selected."""
        return self._coordinator.plans.current_option

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return how the current plan was chosen."""
        plans = self._coordinator.plans
        return {
            ATTR_PLAN_SELECTION_MODE: self._coordinator.config.plan_selection.mode,
            ATTR_PLAN_RESOLVED_AUTOMATICALLY: plans.automatic
            and plans.automatic_available,
            ATTR_OUTDOOR_TEMPERATURE: plans.outdoor_temperature,
        }

    async def async_select_option(self, option: str) -> None:
        """Select a plan, or hand control back to the outdoor sensor."""
        await self._coordinator.async_select_plan(option)
        self.async_write_ha_state()
