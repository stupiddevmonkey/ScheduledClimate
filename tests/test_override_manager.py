"""Unit tests for :class:`OverrideManager` persistence and expiry.

These cover the parts of a hold's lifecycle that are hard to reach through the
climate service (which always clamps a hold to a sensible, future deadline):
restoring a hold across a restart, dropping one that lapsed while Home Assistant
was stopped, refusing a deadline in the past, and cancelling the old expiry
callback when a hold is replaced.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.scheduled_climate.block import ScheduleBlock
from custom_components.scheduled_climate.override import (
    STORAGE_KEY,
    OverrideManager,
    OverrideState,
)

TARGET_KEY = "target-1"
BLOCK = ScheduleBlock(temperature=23.0)


def _recorder() -> tuple[list[datetime], Callable[[datetime], Awaitable[None]]]:
    """Return a list of expiry times and the handler that appends to it."""
    calls: list[datetime] = []

    async def on_expire(now: datetime) -> None:
        calls.append(now)

    return calls, on_expire


def test_override_state_round_trips_to_a_dict() -> None:
    """The stored representation captures the block and the deadline."""
    until = dt_util.utcnow()
    state = OverrideState(block=BLOCK, until=until)

    data = state.as_dict()

    assert data["until"] == until.isoformat()
    assert data["block"] == BLOCK.as_dict()


async def test_hold_is_restored_after_a_restart(hass: HomeAssistant) -> None:
    """A live hold survives a restart and keeps counting down."""
    calls, on_expire = _recorder()
    until = dt_util.utcnow() + timedelta(minutes=30)

    manager = OverrideManager(hass, TARGET_KEY, on_expire)
    await manager.async_set(BLOCK, until)
    # Shutting down only drops the in-memory callback, not the stored hold.
    manager.async_shutdown()

    restored = OverrideManager(hass, TARGET_KEY, on_expire)
    await restored.async_initialize()

    assert restored.active is True
    assert restored.block == BLOCK
    assert restored.until is not None
    assert abs((restored.until - until).total_seconds()) < 1

    # The restored callback still fires at the original deadline.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert len(calls) == 1
    assert restored.active is False


async def test_hold_that_expired_while_stopped_is_dropped(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """A hold whose deadline passed while Home Assistant was down is discarded."""
    calls, on_expire = _recorder()
    manager = OverrideManager(hass, TARGET_KEY, on_expire)
    await manager.async_set(BLOCK, dt_util.utcnow() + timedelta(minutes=30))
    manager.async_shutdown()

    key = f"{STORAGE_KEY}.{TARGET_KEY}"
    hass_storage[key]["data"]["until"] = (
        dt_util.utcnow() - timedelta(minutes=1)
    ).isoformat()

    restored = OverrideManager(hass, TARGET_KEY, on_expire)
    await restored.async_initialize()

    assert restored.active is False
    # The stale hold is removed rather than left to be reloaded again.
    assert key not in hass_storage
    # A dropped hold must not hand control back to the schedule.
    assert calls == []


async def test_hold_with_unparseable_storage_is_dropped(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """A corrupt stored hold is discarded instead of crashing on load."""
    key = f"{STORAGE_KEY}.{TARGET_KEY}"
    hass_storage[key] = {
        "version": 1,
        "minor_version": 1,
        "key": key,
        "data": {"until": "not-a-datetime", "block": {}},
    }

    _calls, on_expire = _recorder()
    manager = OverrideManager(hass, TARGET_KEY, on_expire)
    await manager.async_initialize()

    assert manager.active is False
    assert key not in hass_storage


async def test_setting_a_hold_in_the_past_is_rejected(hass: HomeAssistant) -> None:
    """A hold must end in the future."""
    _calls, on_expire = _recorder()
    manager = OverrideManager(hass, TARGET_KEY, on_expire)

    with pytest.raises(ValueError):
        await manager.async_set(BLOCK, dt_util.utcnow() - timedelta(seconds=1))

    assert manager.active is False


async def test_replacing_a_hold_cancels_the_old_expiry(hass: HomeAssistant) -> None:
    """Setting a new hold cancels the previous one's expiry callback."""
    calls, on_expire = _recorder()
    manager = OverrideManager(hass, TARGET_KEY, on_expire)

    first_deadline = dt_util.utcnow() + timedelta(minutes=10)
    await manager.async_set(BLOCK, first_deadline)

    replacement = ScheduleBlock(temperature=19.0)
    second_deadline = dt_util.utcnow() + timedelta(minutes=20)
    await manager.async_set(replacement, second_deadline)

    # The first deadline passes: the cancelled callback must stay silent.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=11))
    await hass.async_block_till_done()
    assert calls == []
    assert manager.active is True
    assert manager.block == replacement

    # The replacement's deadline fires exactly once.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=21))
    await hass.async_block_till_done()
    assert len(calls) == 1
    assert manager.active is False


async def test_clearing_without_a_hold_is_a_noop(hass: HomeAssistant) -> None:
    """Clearing when nothing is held neither raises nor calls back."""
    calls, on_expire = _recorder()
    manager = OverrideManager(hass, TARGET_KEY, on_expire)

    await manager.async_clear()

    assert manager.active is False
    assert calls == []


async def test_clearing_a_hold_removes_it_without_resuming(
    hass: HomeAssistant,
) -> None:
    """Clearing an active hold drops it but does not fire the expiry handler."""
    calls, on_expire = _recorder()
    manager = OverrideManager(hass, TARGET_KEY, on_expire)
    await manager.async_set(BLOCK, dt_util.utcnow() + timedelta(minutes=30))

    await manager.async_clear()

    assert manager.active is False
    # A cleared hold's deadline must no longer fire.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert calls == []
