"""Shared entity helpers for Scheduled Climate."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def room_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return the device every entity of one room belongs to."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
    )
