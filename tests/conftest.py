"""Shared fixtures and builders for Scheduled Climate tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from homeassistant.components.climate import ATTR_HVAC_MODES, HVACMode
from homeassistant.const import ATTR_SUPPORTED_FEATURES, CONF_NAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scheduled_climate.const import (
    CONF_TARGETS,
    DEFAULT_PLAN_NAME,
    DOMAIN,
)
from custom_components.scheduled_climate.models import (
    OverrideConfig,
    PlanConfig,
    PlanSelectionConfig,
    TargetBehavior,
    TargetConfig,
    build_options,
    new_key,
    targets_as_data,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in tests."""


def make_target(
    entity_id: str, name: str | None = None, *, key: str | None = None
) -> TargetConfig:
    """Return a target for one climate entity, minting a key when needed."""
    return TargetConfig(
        key=key or new_key(),
        entity_id=entity_id,
        name=name or entity_id,
    )


def make_room_entry(
    *,
    title: str = "Living Room",
    targets: Sequence[TargetConfig],
    behaviors: Mapping[str, TargetBehavior] | None = None,
    plans: Sequence[PlanConfig] | None = None,
    plan_selection: PlanSelectionConfig | None = None,
    override: OverrideConfig | None = None,
    legacy_on_time: str | None = None,
    legacy_off_time: str | None = None,
    entry_id: str | None = None,
) -> MockConfigEntry:
    """Return a valid version 3 room config entry for the given targets.

    Options are built with :func:`build_options` so the stored shape always
    matches what the production code parses.
    """
    behaviors = (
        dict(behaviors)
        if behaviors is not None
        else {target.key: TargetBehavior() for target in targets}
    )
    if plans is None:
        plans = [PlanConfig(id=new_key(), name=DEFAULT_PLAN_NAME)]
    plan_selection = plan_selection or PlanSelectionConfig()
    override = override or OverrideConfig()

    options = build_options(
        behaviors=behaviors,
        plans=list(plans),
        plan_selection=plan_selection,
        override=override,
        legacy_on_time=legacy_on_time,
        legacy_off_time=legacy_off_time,
    )

    extra: dict[str, Any] = {}
    if entry_id is not None:
        extra["entry_id"] = entry_id

    return MockConfigEntry(
        domain=DOMAIN,
        version=3,
        title=title,
        data={CONF_NAME: title, CONF_TARGETS: targets_as_data(targets)},
        options=options,
        **extra,
    )


def set_target_state(
    hass: HomeAssistant,
    entity_id: str,
    state: str = HVACMode.HEAT,
    *,
    hvac_modes: Sequence[str] | None = None,
    features: int = 0,
    **attributes: Any,
) -> None:
    """Set a target climate entity state with sensible defaults."""
    if hvac_modes is None:
        hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    hass.states.async_set(
        entity_id,
        state,
        {
            ATTR_HVAC_MODES: list(hvac_modes),
            ATTR_SUPPORTED_FEATURES: features,
            **attributes,
        },
    )
