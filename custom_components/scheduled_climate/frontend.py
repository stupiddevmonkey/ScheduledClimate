"""Frontend registration for Scheduled Climate."""

import asyncio
import logging
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_COMPONENT_LOADED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.setup import ATTR_COMPONENT

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

FRONTEND_DOMAIN = "frontend"
CARD_FILENAME = "scheduled-climate-card.js"
CARD_PATH = f"/{DOMAIN}/{CARD_FILENAME}"
CARD_FILE = Path(__file__).parent / "frontend" / CARD_FILENAME

CARD_URL_CACHE = f"{DOMAIN}_card_url"
STATIC_PATH_REGISTERED = f"{DOMAIN}_static_path_registered"
MODULE_URL_REGISTERED = f"{DOMAIN}_module_url_registered"
MODULE_URL_DEFERRED = f"{DOMAIN}_module_url_deferred"
FRONTEND_REGISTRATION_LOCK = f"{DOMAIN}_frontend_registration_lock"


def _build_card_url() -> str:
    """Build the cache-busted card URL. Reads the bundle from disk."""
    return f"{CARD_PATH}?v={sha256(CARD_FILE.read_bytes()).hexdigest()[:8]}"


async def async_card_url(hass: HomeAssistant) -> str:
    """Return the cache-busted card URL, hashing the bundle only once."""
    cached: str | None = hass.data.get(CARD_URL_CACHE)
    if cached is None:
        cached = await hass.async_add_executor_job(_build_card_url)
        hass.data[CARD_URL_CACHE] = cached
    return cached


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the packaged card and add it to the frontend module URLs.

    Each step is tracked separately and retried on every call so a partial
    registration recovers on the next setup or reload instead of leaving the
    card unreachable until Home Assistant restarts.
    """
    if hass.data.get(STATIC_PATH_REGISTERED) and hass.data.get(MODULE_URL_REGISTERED):
        return

    lock = hass.data.setdefault(FRONTEND_REGISTRATION_LOCK, asyncio.Lock())
    async with lock:
        card_url = await async_card_url(hass)

        if not hass.data.get(STATIC_PATH_REGISTERED):
            await hass.http.async_register_static_paths(
                [StaticPathConfig(CARD_PATH, str(CARD_FILE), cache_headers=True)]
            )
            hass.data[STATIC_PATH_REGISTERED] = True

        _async_add_module_url(hass, card_url)


@callback
def _async_add_module_url(hass: HomeAssistant, card_url: str) -> None:
    """Publish the card URL to the frontend, waiting for it when necessary."""
    if hass.data.get(MODULE_URL_REGISTERED):
        return

    if DATA_EXTRA_MODULE_URL in hass.data:
        add_extra_js_url(hass, card_url)
        hass.data[MODULE_URL_REGISTERED] = True
        return

    if hass.data.get(MODULE_URL_DEFERRED):
        return

    unsub: Callable[[], None] | None = None

    @callback
    def _component_loaded(event: Event) -> None:
        if event.data.get(ATTR_COMPONENT) != FRONTEND_DOMAIN:
            return
        if unsub is not None:
            unsub()
        hass.data[MODULE_URL_DEFERRED] = False
        _async_add_module_url(hass, card_url)

    hass.data[MODULE_URL_DEFERRED] = True
    unsub = hass.bus.async_listen(EVENT_COMPONENT_LOADED, _component_loaded)
    _LOGGER.debug("Frontend not loaded yet, deferring Scheduled Climate card")
