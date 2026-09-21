"""Upgrade-path tests: what happens to an existing deployment on update."""

from __future__ import annotations

from homeassistant.components.climate import (
    ATTR_HVAC_MODES,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.const import ATTR_FRIENDLY_NAME, ATTR_SUPPORTED_FEATURES, CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scheduled_climate.const import (
    CONF_SCHEDULE_ENABLED,
    CONF_SCHEDULE_ENTITY_ID,
    CONF_TARGET_ENTITY_ID,
    DOMAIN,
)

TARGET_ENTITY_ID = "climate.living_room"


def _stub_climate_services(hass: HomeAssistant) -> list[ServiceCall]:
    """Register the climate services a real deployment always has."""
    calls: list[ServiceCall] = []

    async def handler(call: ServiceCall) -> None:
        calls.append(call)

    for service in (SERVICE_SET_HVAC_MODE, SERVICE_SET_TEMPERATURE):
        hass.services.async_register(CLIMATE_DOMAIN, service, handler)
    return calls


def _set_target(hass: HomeAssistant) -> None:
    """Publish the wrapped climate target."""
    hass.states.async_set(
        TARGET_ENTITY_ID,
        HVACMode.HEAT,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT],
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.TARGET_TEMPERATURE,
        },
    )


def _legacy_entry(*, title: str, stored_name: str) -> MockConfigEntry:
    """Return a pre-room entry, as an existing deployment would have it."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        version=2,
        data={CONF_TARGET_ENTITY_ID: TARGET_ENTITY_ID, CONF_NAME: stored_name},
        options={
            CONF_SCHEDULE_ENTITY_ID: "schedule.living_room",
            CONF_SCHEDULE_ENABLED: True,
        },
    )


async def test_upgrade_keeps_the_entity_id_and_display_name(
    hass: HomeAssistant,
) -> None:
    """An untouched deployment keeps its entity id and its friendly name."""
    _set_target(hass)
    _stub_climate_services(hass)
    hass.states.async_set("schedule.living_room", "off")
    entry = _legacy_entry(title="Living Room", stored_name="Living Room")
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    wrapper = er.async_get(hass).async_get_entity_id(
        CLIMATE_DOMAIN, DOMAIN, entry.entry_id
    )
    assert wrapper is not None
    state = hass.states.get(wrapper)
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Living Room"


async def test_upgrade_keeps_the_display_name_after_an_entry_rename(
    hass: HomeAssistant,
) -> None:
    """Renaming the entry in the UI leaves entry.data[name] stale.

    Home Assistant changes only ``entry.title`` when a user renames a config
    entry, so a deployment that was renamed carries a stale ``data[name]``.
    The upgrade must still show the name the user actually sees, rather than
    resurrecting the old one as an entity-name suffix.
    """
    _set_target(hass)
    _stub_climate_services(hass)
    hass.states.async_set("schedule.living_room", "off")
    entry = _legacy_entry(title="Lounge", stored_name="Living Room")
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    wrapper = er.async_get(hass).async_get_entity_id(
        CLIMATE_DOMAIN, DOMAIN, entry.entry_id
    )
    assert wrapper is not None
    state = hass.states.get(wrapper)
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Lounge"
