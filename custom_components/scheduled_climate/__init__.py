"""Scheduled Climate integration."""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_APPLY_ON_START,
    CONF_DEFAULT_HVAC_MODE,
    CONF_LEGACY_OFF_TIME,
    CONF_LEGACY_ON_TIME,
    CONF_OFF_BEHAVIOR,
    CONF_SCHEDULE_ENABLED,
    CONF_SCHEDULE_ENTITY_ID,
    CONF_TARGET_ENTITY_ID,
    CONF_TARGETS,
    DEFAULT_APPLY_ON_START,
    DEFAULT_HVAC_MODE,
    DEFAULT_OFF_BEHAVIOR,
    DEFAULT_PLAN_NAME,
    DEFAULT_SCHEDULE_ENABLED,
    DOMAIN,
)
from .coordinator import RoomCoordinator
from .frontend import async_register_frontend, async_unregister_resource
from .models import (
    OverrideConfig,
    PlanConfig,
    PlanSelectionConfig,
    TargetBehavior,
    TargetConfig,
    build_options,
    new_key,
    targets_as_data,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = (Platform.CLIMATE, Platform.SELECT)

LEGACY_ON_TIME = "on_time"
LEGACY_OFF_TIME = "off_time"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Publish the dashboard card as soon as the component loads."""
    await async_register_frontend(hass)
    return True


def _migrate_options_to_v2(options: dict[str, Any]) -> dict[str, Any]:
    """Move the pre-schedule-helper daily times aside."""
    on_time = options.pop(LEGACY_ON_TIME, None)
    off_time = options.pop(LEGACY_OFF_TIME, None)
    if on_time:
        options[CONF_LEGACY_ON_TIME] = on_time
    if off_time:
        options[CONF_LEGACY_OFF_TIME] = off_time
    options[CONF_SCHEDULE_ENABLED] = False
    options.setdefault(CONF_OFF_BEHAVIOR, DEFAULT_OFF_BEHAVIOR)
    options.setdefault(CONF_APPLY_ON_START, DEFAULT_APPLY_ON_START)
    return options


def _migrate_to_rooms(
    entry: ConfigEntry, data: dict[str, Any], options: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Turn a single-entity entry into a room holding one target and one plan.

    The lone target keeps the entry id as its key so the existing wrapper
    entity, whose unique id is the entry id, survives the upgrade untouched.
    """
    target_entity_id = data.pop(CONF_TARGET_ENTITY_ID, None)
    # Home Assistant changes only the title when a config entry is renamed, so
    # data[name] can be stale. The title is what the user sees, and naming the
    # lone target after it keeps the wrapper entity's friendly name unchanged.
    name = entry.title or data.get(CONF_NAME) or target_entity_id or DOMAIN

    targets: list[TargetConfig] = []
    behaviors: dict[str, TargetBehavior] = {}
    schedules: dict[str, str] = {}

    if target_entity_id:
        key = entry.entry_id
        targets.append(TargetConfig(key=key, entity_id=target_entity_id, name=name))
        behaviors[key] = TargetBehavior(
            schedule_enabled=bool(
                options.get(CONF_SCHEDULE_ENABLED, DEFAULT_SCHEDULE_ENABLED)
            ),
            default_hvac_mode=str(
                options.get(CONF_DEFAULT_HVAC_MODE, DEFAULT_HVAC_MODE)
            ),
            off_behavior=options.get(CONF_OFF_BEHAVIOR, DEFAULT_OFF_BEHAVIOR),
            apply_on_start=bool(
                options.get(CONF_APPLY_ON_START, DEFAULT_APPLY_ON_START)
            ),
        )
        if schedule_entity_id := options.get(CONF_SCHEDULE_ENTITY_ID):
            schedules[key] = schedule_entity_id

    plans = [
        PlanConfig(
            id=new_key(),
            name=DEFAULT_PLAN_NAME,
            schedules=MappingProxyType(schedules),
        )
    ]

    data[CONF_NAME] = name
    data[CONF_TARGETS] = targets_as_data(targets)
    new_options = build_options(
        behaviors=behaviors,
        plans=plans,
        plan_selection=PlanSelectionConfig(),
        override=OverrideConfig(),
        legacy_on_time=options.get(CONF_LEGACY_ON_TIME),
        legacy_off_time=options.get(CONF_LEGACY_OFF_TIME),
    )
    return data, new_options


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a config entry to the current room model."""
    if entry.version > 3:
        return False

    data = dict(entry.data)
    options = dict(entry.options)
    version = entry.version

    if version == 1:
        options = _migrate_options_to_v2(options)
        version = 2
        _LOGGER.info(
            "Migrated %s to the schedule helper model; link a schedule to resume",
            entry.title,
        )

    if version == 2:
        data, options = _migrate_to_rooms(entry, data, options)
        version = 3
        _LOGGER.info(
            "Migrated %s to the room model; it now holds one target and one plan",
            entry.title,
        )

    if version != entry.version:
        hass.config_entries.async_update_entry(
            entry, data=data, options=options, version=version
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Scheduled Climate from a config entry."""
    await async_register_frontend(hass)
    coordinator = RoomCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_initialize()
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Scheduled Climate config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    coordinator: RoomCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    coordinator.async_shutdown()
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
