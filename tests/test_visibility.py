"""Tests for hiding the wrapped climate entities.

Each target is mirrored by a wrapper entity, so the wrapped entity is hidden
while the wrapper exists - the same approach Home Assistant's own
``switch_as_x`` integration uses. Hiding is a user-interface concern only.
"""

from __future__ import annotations

from homeassistant.components.climate import (
    ATTR_HVAC_MODES,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scheduled_climate.const import (
    CONF_HIDE_TARGETS,
    DOMAIN,
)
from custom_components.scheduled_climate.models import (
    OverrideConfig,
    PlanConfig,
    PlanSelectionConfig,
    TargetBehavior,
    TargetConfig,
    build_options,
    targets_as_data,
)

MINI_SPLIT = "climate.mini_split"
RADIANT = "climate.radiant_heater"
MINI_KEY = "mini"
RADIANT_KEY = "radiant"


def _register(hass: HomeAssistant, entity_id: str, unique_id: str) -> str:
    """Register a real climate entity so it has a registry entry to hide."""
    registry = er.async_get(hass)
    entry = registry.async_get_or_create(
        CLIMATE_DOMAIN,
        "demo",
        unique_id,
        suggested_object_id=entity_id.split(".", 1)[1],
    )
    hass.states.async_set(
        entry.entity_id,
        HVACMode.HEAT,
        {
            ATTR_HVAC_MODES: [HVACMode.OFF, HVACMode.HEAT],
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.TARGET_TEMPERATURE,
        },
    )
    return entry.entity_id


def _entry(*, hide: bool = True) -> MockConfigEntry:
    """Return a two-target room entry."""
    targets = [
        TargetConfig(key=MINI_KEY, entity_id=MINI_SPLIT, name="Mini split"),
        TargetConfig(key=RADIANT_KEY, entity_id=RADIANT, name="Radiant heater"),
    ]
    return MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        version=3,
        data={"name": "Living Room", "targets": targets_as_data(targets)},
        options=build_options(
            behaviors={
                MINI_KEY: TargetBehavior(apply_on_start=False),
                RADIANT_KEY: TargetBehavior(apply_on_start=False),
            },
            plans=[PlanConfig(id="default", name="Default")],
            plan_selection=PlanSelectionConfig(),
            override=OverrideConfig(),
            hide_targets=hide,
        ),
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add and set up a room entry."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _hidden_by(hass: HomeAssistant, entity_id: str):
    """Return the hidden_by value for one entity."""
    entry = er.async_get(hass).async_get(entity_id)
    assert entry is not None
    return entry.hidden_by


async def test_wrapped_entities_are_hidden(hass: HomeAssistant) -> None:
    """Setting up a room hides the thermostats it wraps."""
    _register(hass, MINI_SPLIT, "mini-uid")
    _register(hass, RADIANT, "radiant-uid")

    await _setup(hass, _entry())

    assert _hidden_by(hass, MINI_SPLIT) is er.RegistryEntryHider.INTEGRATION
    assert _hidden_by(hass, RADIANT) is er.RegistryEntryHider.INTEGRATION

    # The wrappers themselves stay visible - they are what the user controls.
    registry = er.async_get(hass)
    wrapper = registry.async_get_entity_id(CLIMATE_DOMAIN, DOMAIN, MINI_KEY)
    assert wrapper is not None
    assert registry.async_get(wrapper).hidden_by is None


async def test_opting_out_leaves_them_visible(hass: HomeAssistant) -> None:
    """A room configured not to hide leaves the thermostats alone."""
    _register(hass, MINI_SPLIT, "mini-uid")
    _register(hass, RADIANT, "radiant-uid")

    await _setup(hass, _entry(hide=False))

    assert _hidden_by(hass, MINI_SPLIT) is None
    assert _hidden_by(hass, RADIANT) is None


async def test_a_user_hidden_entity_is_not_touched(hass: HomeAssistant) -> None:
    """A thermostat the user hid stays hidden by the user, not by us.

    This matters on removal: only entities hidden by the integration are
    revealed again, so a user's own choice must never be overwritten.
    """
    _register(hass, MINI_SPLIT, "mini-uid")
    _register(hass, RADIANT, "radiant-uid")
    er.async_get(hass).async_update_entity(
        MINI_SPLIT, hidden_by=er.RegistryEntryHider.USER
    )

    await _setup(hass, _entry())

    assert _hidden_by(hass, MINI_SPLIT) is er.RegistryEntryHider.USER
    assert _hidden_by(hass, RADIANT) is er.RegistryEntryHider.INTEGRATION


async def test_removing_the_entry_reveals_them(hass: HomeAssistant) -> None:
    """Uninstalling must never leave a thermostat hidden with no wrapper."""
    _register(hass, MINI_SPLIT, "mini-uid")
    _register(hass, RADIANT, "radiant-uid")
    entry = _entry()
    await _setup(hass, entry)
    assert _hidden_by(hass, MINI_SPLIT) is er.RegistryEntryHider.INTEGRATION

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert _hidden_by(hass, MINI_SPLIT) is None
    assert _hidden_by(hass, RADIANT) is None


async def test_removing_the_entry_keeps_a_user_hidden_entity_hidden(
    hass: HomeAssistant,
) -> None:
    """Removal only undoes the hiding this integration performed."""
    _register(hass, MINI_SPLIT, "mini-uid")
    _register(hass, RADIANT, "radiant-uid")
    er.async_get(hass).async_update_entity(
        MINI_SPLIT, hidden_by=er.RegistryEntryHider.USER
    )
    entry = _entry()
    await _setup(hass, entry)

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert _hidden_by(hass, MINI_SPLIT) is er.RegistryEntryHider.USER
    assert _hidden_by(hass, RADIANT) is None


async def test_toggling_the_option_reveals_them(hass: HomeAssistant) -> None:
    """Turning the option off reveals the thermostats on the next reload."""
    _register(hass, MINI_SPLIT, "mini-uid")
    _register(hass, RADIANT, "radiant-uid")
    entry = _entry()
    await _setup(hass, entry)
    assert _hidden_by(hass, MINI_SPLIT) is er.RegistryEntryHider.INTEGRATION

    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_HIDE_TARGETS: False}
    )
    await hass.async_block_till_done()

    assert _hidden_by(hass, MINI_SPLIT) is None
    assert _hidden_by(hass, RADIANT) is None
