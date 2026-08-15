"""Tests for Scheduled Climate frontend registration."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_COMPONENT_LOADED
from homeassistant.core import HomeAssistant
from homeassistant.setup import ATTR_COMPONENT, async_setup_component

from custom_components.scheduled_climate.const import DOMAIN
from custom_components.scheduled_climate.frontend import (
    CARD_PATH,
    FRONTEND_DOMAIN,
    MODULE_URL_REGISTERED,
    STATIC_PATH_REGISTERED,
    async_card_url,
    async_register_frontend,
)


def _build_hass(*, frontend_loaded: bool = True) -> Mock:
    """Return a hass mock with the pieces frontend registration touches."""
    hass = Mock()
    hass.data = {DATA_EXTRA_MODULE_URL: Mock()} if frontend_loaded else {}
    hass.http.async_register_static_paths = AsyncMock()
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda target, *args: target(*args)
    )
    return hass


async def test_register_frontend_once() -> None:
    """Test the packaged card path and module URL are registered once."""
    hass = _build_hass()

    await async_register_frontend(hass)
    await async_register_frontend(hass)

    hass.http.async_register_static_paths.assert_awaited_once()
    path_config = hass.http.async_register_static_paths.await_args.args[0][0]
    assert isinstance(path_config, StaticPathConfig)
    assert path_config.url_path == CARD_PATH
    assert Path(path_config.path).is_file()
    assert path_config.cache_headers is True

    card_url = await async_card_url(hass)
    assert card_url.startswith(f"{CARD_PATH}?v=")
    hass.data[DATA_EXTRA_MODULE_URL].add.assert_called_once_with(card_url)
    assert hass.data[STATIC_PATH_REGISTERED] is True
    assert hass.data[MODULE_URL_REGISTERED] is True


async def test_card_url_hashed_once() -> None:
    """Test the bundle is only hashed once per Home Assistant instance."""
    hass = _build_hass()

    first = await async_card_url(hass)
    second = await async_card_url(hass)

    assert first == second
    hass.async_add_executor_job.assert_awaited_once()


async def test_register_frontend_once_during_concurrent_entry_setup() -> None:
    """Test concurrent config entries cannot register the route twice."""
    registration_started = asyncio.Event()
    allow_registration = asyncio.Event()

    async def register_static_paths(_configs: list[StaticPathConfig]) -> None:
        registration_started.set()
        await allow_registration.wait()

    hass = _build_hass()
    hass.http.async_register_static_paths = AsyncMock(side_effect=register_static_paths)

    registrations = [
        asyncio.create_task(async_register_frontend(hass)) for _ in range(3)
    ]
    await registration_started.wait()
    await asyncio.sleep(0)
    allow_registration.set()
    await asyncio.gather(*registrations)

    hass.http.async_register_static_paths.assert_awaited_once()
    hass.data[DATA_EXTRA_MODULE_URL].add.assert_called_once()
    assert hass.data[STATIC_PATH_REGISTERED] is True
    assert hass.data[MODULE_URL_REGISTERED] is True


async def test_register_frontend_waits_for_frontend_component() -> None:
    """Test the card is published as soon as the frontend finishes loading."""
    hass = _build_hass(frontend_loaded=False)
    unsub = Mock()
    hass.bus.async_listen = Mock(return_value=unsub)

    await async_register_frontend(hass)

    hass.http.async_register_static_paths.assert_awaited_once()
    assert hass.data[STATIC_PATH_REGISTERED] is True
    assert MODULE_URL_REGISTERED not in hass.data
    assert hass.bus.async_listen.call_args.args[0] == EVENT_COMPONENT_LOADED

    listener = hass.bus.async_listen.call_args.args[1]
    url_manager = Mock()
    hass.data[DATA_EXTRA_MODULE_URL] = url_manager

    listener(Mock(data={ATTR_COMPONENT: "sensor"}))
    url_manager.add.assert_not_called()

    listener(Mock(data={ATTR_COMPONENT: FRONTEND_DOMAIN}))
    unsub.assert_called_once()
    url_manager.add.assert_called_once_with(await async_card_url(hass))
    assert hass.data[MODULE_URL_REGISTERED] is True


async def test_register_frontend_defers_only_once() -> None:
    """Test repeated setups do not stack frontend listeners."""
    hass = _build_hass(frontend_loaded=False)
    hass.bus.async_listen = Mock(return_value=Mock())

    await async_register_frontend(hass)
    await async_register_frontend(hass)

    hass.bus.async_listen.assert_called_once()
    hass.http.async_register_static_paths.assert_awaited_once()


async def test_card_served_without_config_entry(hass: HomeAssistant) -> None:
    """Test the card is served from component setup, before any entry loads."""
    assert await async_setup_component(hass, DOMAIN, {})

    assert hass.data[STATIC_PATH_REGISTERED] is True
