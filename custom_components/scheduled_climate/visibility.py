"""Wrapped entity visibility for Scheduled Climate.

Each target is mirrored by a wrapper ``climate`` entity, so leaving the wrapped
entity visible shows every thermostat twice in pickers, voice assistants and
auto-generated dashboards. Home Assistant's own wrapper integration
(``switch_as_x``) solves this by hiding the wrapped entity while the wrapper
exists and revealing it again afterwards; this module does the same.

Hiding only affects the user interface. Automations, scripts, the REST and
websocket APIs, and recorder history all continue to address the wrapped entity
exactly as before.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)


@callback
def async_hide_targets(hass: HomeAssistant, entity_ids: Iterable[str]) -> None:
    """Hide the wrapped climate entities behind their wrappers."""
    registry = er.async_get(hass)
    for entity_id in entity_ids:
        entry = registry.async_get(entity_id)
        if entry is None or entry.hidden_by is not None:
            # Missing, or already hidden - never override a user's own choice.
            continue
        registry.async_update_entity(
            entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
        )
        _LOGGER.debug("Hid %s behind its Scheduled Climate wrapper", entity_id)


@callback
def async_unhide_targets(hass: HomeAssistant, entity_ids: Iterable[str]) -> None:
    """Reveal wrapped climate entities that this integration hid."""
    registry = er.async_get(hass)
    for entity_id in entity_ids:
        entry = registry.async_get(entity_id)
        if entry is None or entry.hidden_by is not er.RegistryEntryHider.INTEGRATION:
            # Only undo our own hiding; a user-hidden entity stays hidden.
            continue
        registry.async_update_entity(entity_id, hidden_by=None)
        _LOGGER.debug("Revealed %s after its wrapper went away", entity_id)
