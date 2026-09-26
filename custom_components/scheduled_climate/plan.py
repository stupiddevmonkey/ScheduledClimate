"""Active plan resolution for Scheduled Climate.

A room can hold several named plans - a warm-month plan that cools and a
cool-month plan that heats, for example. The ``select`` entity is the single
source of truth for which plan is active. When it sits on *Automatic* the plan
is derived from an outdoor temperature sensor: plans form ascending temperature
bands, a hysteresis band stops the selection flapping at a boundary, and a
sustain delay ignores brief excursions.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    ISSUE_NO_PLANS,
    ISSUE_OUTDOOR_SENSOR_UNAVAILABLE,
    PLAN_AUTOMATIC,
)
from .models import PlanConfig, RoomConfig

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "scheduled_climate_plan"
STORAGE_SELECTION = "selection"
STORAGE_RESOLVED = "resolved"

UNUSABLE_STATES = frozenset({STATE_UNAVAILABLE, STATE_UNKNOWN})

PLAN_ISSUES = (ISSUE_NO_PLANS, ISSUE_OUTDOOR_SENSOR_UNAVAILABLE)


class PlanStorageData(TypedDict, total=False):
    """Stored plan selection state."""

    selection: str
    resolved: str


def _as_temperature(value: Any) -> float | None:
    """Return a usable outdoor temperature reading, or None."""
    if not isinstance(value, str) or value in UNUSABLE_STATES:
        return None
    try:
        return float(value)
    except ValueError:
        return None


class PlanSelector:
    """Decide which plan a room follows and publish changes."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        config: RoomConfig,
    ) -> None:
        """Initialize the plan selector."""
        self.hass = hass
        self.entry = entry
        self._config = config
        self._selection: str = PLAN_AUTOMATIC
        self._resolved_id: str | None = None
        self._pending_id: str | None = None
        self._cancel_sustain: Callable[[], None] | None = None
        self._cancel_sensor: Callable[[], None] | None = None
        self._listeners: list[Callable[[], None]] = []
        self._store = Store[PlanStorageData](
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}.{entry.entry_id}",
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_initialize(self) -> None:
        """Restore the stored selection and resolve the active plan."""
        stored = await self._store.async_load()
        if stored:
            selection = stored.get(STORAGE_SELECTION)
            # A plan deleted since the last run must not leave the room stuck
            # on a selection that can never resolve.
            if (
                isinstance(selection, str)
                and selection
                and (
                    selection == PLAN_AUTOMATIC
                    or self._config.plan_by_id(selection) is not None
                )
            ):
                self._selection = selection
            resolved = stored.get(STORAGE_RESOLVED)
            if isinstance(resolved, str) and self._config.plan_by_id(resolved):
                self._resolved_id = resolved

        self._async_track_sensor()
        self._async_resolve(immediate=True, notify=False)
        self._async_update_issues()

    @callback
    def async_shutdown(self) -> None:
        """Cancel every registered callback."""
        self._cancel_pending()
        if self._cancel_sensor is not None:
            self._cancel_sensor()
            self._cancel_sensor = None
        self._listeners.clear()
        for issue in PLAN_ISSUES:
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_id(issue))

    # ------------------------------------------------------------------
    # Public view
    # ------------------------------------------------------------------

    @property
    def automatic(self) -> bool:
        """Return whether the selection is left to the outdoor temperature."""
        return self._selection == PLAN_AUTOMATIC

    @property
    def automatic_available(self) -> bool:
        """Return whether an automatic rule is configured."""
        return self._config.plan_selection.automatic_available

    @property
    def active_plan(self) -> PlanConfig | None:
        """Return the plan currently driving every target in the room."""
        return self._config.plan_by_id(self._resolved_id)

    @property
    def options(self) -> list[str]:
        """Return the options offered by the select entity."""
        names = list(self._config.plan_names)
        if self.automatic_available:
            return [PLAN_AUTOMATIC, *names]
        return names

    @property
    def current_option(self) -> str | None:
        """Return the select entity's current option."""
        if self.automatic and self.automatic_available:
            return PLAN_AUTOMATIC
        plan = self.active_plan
        return plan.name if plan else None

    def schedule_entity_id(self, target_key: str) -> str | None:
        """Return the schedule helper the active plan uses for one target."""
        plan = self.active_plan
        return plan.schedule_for(target_key) if plan else None

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a callback fired when the active plan changes."""
        self._listeners.append(listener)

        @callback
        def remove_listener() -> None:
            """Remove the registered callback."""
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    @callback
    def _notify_listeners(self) -> None:
        """Notify registered listeners that the active plan changed."""
        for listener in list(self._listeners):
            listener()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    async def async_select(self, option: str) -> bool:
        """Pick a plan by name, or hand control back to the outdoor sensor.

        Returns whether the resolved plan changed.
        """
        previous = self._resolved_id
        if option == PLAN_AUTOMATIC:
            self._selection = PLAN_AUTOMATIC
            self._async_resolve(immediate=True, notify=False)
        else:
            plan = self._config.plan_by_name(option)
            if plan is None:
                raise ValueError(f"Unknown plan '{option}'")
            self._cancel_pending()
            self._selection = plan.id
            self._resolved_id = plan.id

        await self._async_save()
        self._async_update_issues()
        changed = previous != self._resolved_id
        self._notify_listeners()
        return changed

    # ------------------------------------------------------------------
    # Automatic resolution
    # ------------------------------------------------------------------

    @callback
    def _async_track_sensor(self) -> None:
        """Subscribe to the configured outdoor temperature sensor."""
        if self._cancel_sensor is not None:
            self._cancel_sensor()
            self._cancel_sensor = None

        entity_id = self._config.plan_selection.outdoor_temp_entity_id
        if entity_id is None:
            return
        self._cancel_sensor = async_track_state_change_event(
            self.hass, [entity_id], self._async_sensor_changed
        )

    @callback
    def _async_sensor_changed(self, _event: Event[EventStateChangedData]) -> None:
        """Re-resolve the active plan after an outdoor reading."""
        self._async_resolve()
        self._async_update_issues()

    @property
    def outdoor_temperature(self) -> float | None:
        """Return the current outdoor reading, or None when unusable."""
        entity_id = self._config.plan_selection.outdoor_temp_entity_id
        if entity_id is None:
            return None
        state = self.hass.states.get(entity_id)
        return _as_temperature(state.state) if state else None

    def _band_for(self, temperature: float) -> PlanConfig | None:
        """Return the plan whose temperature band holds the reading.

        Plans are tried most specific first, so a plan naming both ends of a
        band beats one naming a single end, which beats the unbounded
        fallback.

        A hysteresis dead zone straddles every boundary. To take over, a more
        specific plan must match its band narrowed by half the hysteresis, so
        the reading is clearly inside it. To keep its place, the plan already
        in force only has to match its band widened by the same amount. A
        reading hovering on a boundary therefore leaves the plan unchanged.
        """
        candidates = self._config.match_order
        if not candidates:
            return None

        half = self._config.plan_selection.hysteresis / 2
        current = self.active_plan

        if current is not None:
            challenger = next(
                (
                    plan
                    for plan in candidates
                    if plan is not current
                    and plan.match_rank < current.match_rank
                    and plan.matches(temperature, widen=-half)
                ),
                None,
            )
            if challenger is not None:
                return challenger
            if current.matches(temperature, widen=half):
                return current

        best = next((plan for plan in candidates if plan.matches(temperature)), None)
        if best is not None:
            return best

        # Every band excludes the reading, which only happens when the plans
        # leave a gap. Hold the current plan rather than dropping the room's
        # schedule, and otherwise fall back to the nearest band.
        return current or self._nearest_band(temperature)

    def _nearest_band(self, temperature: float) -> PlanConfig | None:
        """Return the plan whose band sits closest to an uncovered reading."""

        def distance(plan: PlanConfig) -> float:
            low = plan.min_outdoor_temp
            high = plan.max_outdoor_temp
            if low is not None and temperature < low:
                return low - temperature
            if high is not None and temperature >= high:
                return temperature - high
            return 0.0

        ordered = self._config.ordered_plans
        return min(ordered, key=distance) if ordered else None

    def _candidate(self) -> PlanConfig | None:
        """Return the plan the current configuration and reading imply."""
        if not self._config.plans:
            return None
        if not self.automatic or not self.automatic_available:
            plan = self._config.plan_by_id(self._selection)
            if plan is not None:
                return plan
            return self.active_plan or self._config.ordered_plans[0]

        temperature = self.outdoor_temperature
        if temperature is None:
            # Hold the last resolved plan rather than guessing.
            return self.active_plan or self._config.ordered_plans[0]
        return self._band_for(temperature)

    @callback
    def _async_resolve(self, *, immediate: bool = False, notify: bool = True) -> None:
        """Move to the implied plan, respecting the sustain delay."""
        candidate = self._candidate()
        if candidate is None:
            self._cancel_pending()
            if self._resolved_id is not None:
                self._resolved_id = None
                if notify:
                    self._notify_listeners()
            return

        if candidate.id == self._resolved_id:
            self._cancel_pending()
            return

        sustain = self._config.plan_selection.sustain_minutes
        if immediate or not self.automatic or sustain <= 0:
            self._cancel_pending()
            self._async_commit(candidate.id, notify=notify)
            return

        if self._pending_id == candidate.id:
            return

        self._cancel_pending()
        self._pending_id = candidate.id
        self._cancel_sustain = async_call_later(
            self.hass, timedelta(minutes=sustain), self._async_sustain_elapsed
        )

    @callback
    def _async_sustain_elapsed(self, _now: datetime) -> None:
        """Commit a candidate that held for the whole sustain window."""
        self._cancel_sustain = None
        pending = self._pending_id
        self._pending_id = None
        if pending is None:
            return

        candidate = self._candidate()
        if candidate is not None and candidate.id == pending:
            self._async_commit(pending)

    @callback
    def _async_commit(self, plan_id: str, *, notify: bool = True) -> None:
        """Record a new active plan and tell everyone about it."""
        if plan_id == self._resolved_id:
            return
        self._resolved_id = plan_id
        self.hass.async_create_task(self._async_save())
        _LOGGER.debug(
            "%s is now following the '%s' plan",
            self.entry.title,
            self.active_plan.name if self.active_plan else plan_id,
        )
        if notify:
            self._notify_listeners()

    @callback
    def _cancel_pending(self) -> None:
        """Cancel a sustain window that is no longer relevant."""
        if self._cancel_sustain is not None:
            self._cancel_sustain()
            self._cancel_sustain = None
        self._pending_id = None

    async def _async_save(self) -> None:
        """Persist the selection so a restart does not change plans."""
        data: PlanStorageData = {STORAGE_SELECTION: self._selection}
        if self._resolved_id is not None:
            data[STORAGE_RESOLVED] = self._resolved_id
        await self._store.async_save(data)

    # ------------------------------------------------------------------
    # Repairs
    # ------------------------------------------------------------------

    def _issue_id(self, issue: str) -> str:
        """Return the repair issue id for this config entry."""
        return f"{issue}_{self.entry.entry_id}"

    @callback
    def _async_update_issues(self) -> None:
        """Create or resolve plan selection repair issues."""
        placeholders = {"name": self.entry.title}

        self._async_set_issue(ISSUE_NO_PLANS, not self._config.plans, placeholders)
        self._async_set_issue(
            ISSUE_OUTDOOR_SENSOR_UNAVAILABLE,
            self.automatic
            and self.automatic_available
            and self.outdoor_temperature is None,
            {
                **placeholders,
                "entity_id": self._config.plan_selection.outdoor_temp_entity_id or "",
            },
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
