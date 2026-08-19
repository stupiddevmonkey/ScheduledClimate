"""Frontend registration for Scheduled Climate."""

import asyncio
import logging
from hashlib import sha256
from pathlib import Path

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import (
    CONF_RESOURCE_TYPE_WS,
    LOVELACE_DATA,
)
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.const import CONF_ID, CONF_URL
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "scheduled-climate-card.js"
CARD_PATH = f"/{DOMAIN}/{CARD_FILENAME}"
CARD_FILE = Path(__file__).parent / "frontend" / CARD_FILENAME
RESOURCE_TYPE_MODULE = "module"

STATIC_PATH_REGISTERED = f"{DOMAIN}_static_path_registered"
FRONTEND_REGISTRATION_LOCK = f"{DOMAIN}_frontend_registration_lock"


def _build_card_url() -> str:
    """Build the cache-busted card URL. Reads the bundle from disk."""
    return f"{CARD_PATH}?v={sha256(CARD_FILE.read_bytes()).hexdigest()[:8]}"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the packaged card and register it as a dashboard resource.

    The card is added through the same storage-backed Lovelace resource
    mechanism used for resources added by hand from the UI. The frontend
    reads that list from its own storage on every dashboard load, so the
    card does not depend on this integration having already finished
    setting up by the time a client loads a dashboard -- unlike the
    in-memory extra module URL list, which left the card unreachable for
    any client that connected in the window before this integration
    finished registering it.
    """
    lock = hass.data.setdefault(FRONTEND_REGISTRATION_LOCK, asyncio.Lock())
    async with lock:
        if not hass.data.get(STATIC_PATH_REGISTERED):
            await hass.http.async_register_static_paths(
                [StaticPathConfig(CARD_PATH, str(CARD_FILE), cache_headers=True)]
            )
            hass.data[STATIC_PATH_REGISTERED] = True

        card_url = await hass.async_add_executor_job(_build_card_url)
        await _async_ensure_resource(hass, card_url)


async def _async_ensure_resource(hass: HomeAssistant, card_url: str) -> None:
    """Create or update the persisted Lovelace resource for the card."""
    lovelace = hass.data.get(LOVELACE_DATA)
    resources = lovelace.resources if lovelace else None
    if not isinstance(resources, ResourceStorageCollection):
        # YAML-mode Lovelace (or the lovelace component is not set up) has no
        # storage collection to write to; fall back to the module URL list.
        if DATA_EXTRA_MODULE_URL in hass.data:
            add_extra_js_url(hass, card_url)
        return

    await resources.async_get_info()  # Ensures the collection is loaded.
    for item in resources.async_items():
        if not str(item.get(CONF_URL, "")).startswith(CARD_PATH):
            continue
        if item[CONF_URL] != card_url:
            await resources.async_update_item(item[CONF_ID], {CONF_URL: card_url})
        return

    await resources.async_create_item(
        {CONF_RESOURCE_TYPE_WS: RESOURCE_TYPE_MODULE, CONF_URL: card_url}
    )


async def async_unregister_resource(hass: HomeAssistant) -> None:
    """Remove the persisted Lovelace resource for the card."""
    lovelace = hass.data.get(LOVELACE_DATA)
    resources = lovelace.resources if lovelace else None
    if not isinstance(resources, ResourceStorageCollection):
        return

    await resources.async_get_info()
    for item in list(resources.async_items()):
        if str(item.get(CONF_URL, "")).startswith(CARD_PATH):
            await resources.async_delete_item(item[CONF_ID])
