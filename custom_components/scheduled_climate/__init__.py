"""Scheduled Climate integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_APPLY_ON_START,
    CONF_LEGACY_OFF_TIME,
    CONF_LEGACY_ON_TIME,
    CONF_OFF_BEHAVIOR,
    CONF_SCHEDULE_ENABLED,
    DEFAULT_APPLY_ON_START,
    DEFAULT_OFF_BEHAVIOR,
    DOMAIN,
)
from .frontend import async_register_frontend, async_unregister_resource
from .schedule import ScheduleManager

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = (Platform.CLIMATE,)

LEGACY_ON_TIME = "on_time"
LEGACY_OFF_TIME = "off_time"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Publish the dashboard card as soon as the component loads."""
    await async_register_frontend(hass)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a config entry to the schedule helper model."""
    if entry.version > 2:
        return False

    if entry.version == 1:
        options = dict(entry.options)
        on_time = options.pop(LEGACY_ON_TIME, None)
        off_time = options.pop(LEGACY_OFF_TIME, None)
        if on_time:
            options[CONF_LEGACY_ON_TIME] = on_time
        if off_time:
            options[CONF_LEGACY_OFF_TIME] = off_time
        options[CONF_SCHEDULE_ENABLED] = False
        options.setdefault(CONF_OFF_BEHAVIOR, DEFAULT_OFF_BEHAVIOR)
        options.setdefault(CONF_APPLY_ON_START, DEFAULT_APPLY_ON_START)
        hass.config_entries.async_update_entry(entry, options=options, version=2)
        _LOGGER.info(
            "Migrated %s to the schedule helper model; link a schedule to resume",
            entry.title,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Scheduled Climate from a config entry."""
    await async_register_frontend(hass)
    manager = ScheduleManager(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager
    await manager.async_initialize()
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Scheduled Climate config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    manager: ScheduleManager = hass.data[DOMAIN].pop(entry.entry_id)
    manager.async_shutdown()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the dashboard resource once the last config entry is gone."""
    other_entries = [
        candidate
        for candidate in hass.config_entries.async_entries(DOMAIN)
        if candidate.entry_id != entry.entry_id
    ]
    if not other_entries:
        await async_unregister_resource(hass)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Scheduled Climate after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
