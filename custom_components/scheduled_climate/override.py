"""Temporary holds for Scheduled Climate.

A hold ("override") lets any user - including non-administrators, who can never
write to a Home Assistant ``schedule`` helper - park a climate target at chosen
settings for a while. The schedule is suppressed until the hold expires, at
which point the controller resumes whatever the schedule asks for.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypedDict

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .block import ScheduleBlock

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "scheduled_climate_override"
STORAGE_UNTIL = "until"
STORAGE_BLOCK = "block"

ExpiryHandler = Callable[[datetime], Awaitable[None]]


class OverrideStorageData(TypedDict):
    """Stored hold state."""

    until: str
    block: dict[str, Any]


@dataclass(frozen=True, slots=True)
class OverrideState:
    """An active hold: the requested settings and when they lapse."""

    block: ScheduleBlock
    until: datetime

    def as_dict(self) -> dict[str, Any]:
        """Return the diagnostics and attribute representation."""
        return {
            "until": self.until.isoformat(),
            "block": self.block.as_dict(),
        }


class OverrideManager:
    """Own one persisted hold for a single climate target."""

    def __init__(
        self,
        hass: HomeAssistant,
        target_key: str,
        on_expire: ExpiryHandler,
    ) -> None:
        """Initialize the override manager."""
        self.hass = hass
        self._on_expire = on_expire
        self._state: OverrideState | None = None
        self._cancel_callback: Callable[[], None] | None = None
        self._store = Store[OverrideStorageData](
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}.{target_key}",
        )

    @property
    def state(self) -> OverrideState | None:
        """Return the active hold, if any."""
        return self._state

    @property
    def active(self) -> bool:
        """Return whether a hold is currently suppressing the schedule."""
        return self._state is not None

    @property
    def until(self) -> datetime | None:
        """Return when the active hold lapses."""
        return self._state.until if self._state else None

    @property
    def block(self) -> ScheduleBlock | None:
        """Return the settings the active hold requests."""
        return self._state.block if self._state else None

    async def async_initialize(self) -> None:
        """Restore a hold that survived a restart, dropping stale ones."""
        stored = await self._store.async_load()
        if not stored:
            return

        until = dt_util.parse_datetime(stored.get(STORAGE_UNTIL, "") or "")
        raw_block = stored.get(STORAGE_BLOCK)
        if until is None or until.tzinfo is None or not isinstance(raw_block, dict):
            await self._store.async_remove()
            return

        until = until.astimezone(UTC)
        if until <= dt_util.utcnow():
            await self._store.async_remove()
            return

        self._state = OverrideState(
            block=ScheduleBlock.from_dict(raw_block), until=until
        )
        self._schedule_callback()

    async def async_set(self, block: ScheduleBlock, until: datetime) -> None:
        """Start or replace the hold."""
        deadline = dt_util.as_utc(until)
        if deadline <= dt_util.utcnow():
            raise ValueError("A hold must end in the future")

        self._cancel_scheduled_callback()
        self._state = OverrideState(block=block, until=deadline)
        await self._store.async_save(
            {
                STORAGE_UNTIL: deadline.isoformat(),
                STORAGE_BLOCK: block.as_dict(),
            }
        )
        self._schedule_callback()

    async def async_clear(self) -> None:
        """Cancel the active hold without resuming anything."""
        self._cancel_scheduled_callback()
        if self._state is None:
            return
        self._state = None
        await self._store.async_remove()

    @callback
    def async_shutdown(self) -> None:
        """Cancel the in-memory callback without clearing persisted state."""
        self._cancel_scheduled_callback()

    @callback
    def _schedule_callback(self) -> None:
        """Schedule the expiry callback for the active hold."""
        if self._state is None:
            return
        self._cancel_callback = async_track_point_in_utc_time(
            self.hass,
            self._async_expire,
            self._state.until,
        )

    @callback
    def _cancel_scheduled_callback(self) -> None:
        """Cancel the active in-memory callback."""
        if self._cancel_callback is not None:
            self._cancel_callback()
            self._cancel_callback = None

    async def _async_expire(self, now: datetime) -> None:
        """Consume the hold once and hand control back to the schedule."""
        if self._state is None:
            return

        self._cancel_callback = None
        self._state = None
        await self._store.async_remove()
        _LOGGER.debug("Hold expired, resuming the schedule")
        await self._on_expire(now)
