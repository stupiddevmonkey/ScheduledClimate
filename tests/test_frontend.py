"""Tests for Scheduled Climate frontend registration."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scheduled_climate.const import CONF_TARGET_ENTITY_ID, DOMAIN
from custom_components.scheduled_climate.frontend import (
    CARD_PATH,
    STATIC_PATH_REGISTERED,
    async_register_frontend,
    async_unregister_resource,
)


def _resource_urls(hass: HomeAssistant) -> list[str]:
    """Return the registered resource URLs pointing at the card."""
    resources = hass.data[LOVELACE_DATA].resources
    assert isinstance(resources, ResourceStorageCollection)
    return [
        item[CONF_URL]
        for item in resources.async_items()
        if item[CONF_URL].startswith(CARD_PATH)
    ]


async def test_register_frontend_creates_dashboard_resource(
    hass: HomeAssistant,
) -> None:
    """Test the packaged card is served and added as a Lovelace resource."""
    assert await async_setup_component(hass, "lovelace", {})

    await async_register_frontend(hass)

    urls = _resource_urls(hass)
    assert len(urls) == 1
    assert urls[0].startswith(f"{CARD_PATH}?v=")
    assert hass.data[STATIC_PATH_REGISTERED] is True


async def test_register_frontend_is_idempotent(hass: HomeAssistant) -> None:
    """Test repeated registration does not create duplicate resources."""
    assert await async_setup_component(hass, "lovelace", {})

    await async_register_frontend(hass)
    await async_register_frontend(hass)

    assert len(_resource_urls(hass)) == 1


async def test_register_frontend_once_during_concurrent_entry_setup(
    hass: HomeAssistant,
) -> None:
    """Test concurrent config entries cannot register duplicate resources."""
    assert await async_setup_component(hass, "lovelace", {})
    registration_started = asyncio.Event()
    allow_registration = asyncio.Event()
    real_register_static_paths = hass.http.async_register_static_paths

    async def register_static_paths(configs: list[StaticPathConfig]) -> None:
        registration_started.set()
        await allow_registration.wait()
        await real_register_static_paths(configs)

    hass.http.async_register_static_paths = AsyncMock(side_effect=register_static_paths)

    registrations = [
        asyncio.create_task(async_register_frontend(hass)) for _ in range(3)
    ]
    await registration_started.wait()
    await asyncio.sleep(0)
    allow_registration.set()
    await asyncio.gather(*registrations)

    hass.http.async_register_static_paths.assert_awaited_once()
    assert len(_resource_urls(hass)) == 1


async def test_register_frontend_falls_back_without_storage_collection() -> None:
    """Test the module URL list is used when Lovelace has no storage collection."""
    hass = Mock()
    hass.data = {DATA_EXTRA_MODULE_URL: Mock()}
    hass.http.async_register_static_paths = AsyncMock()
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda target, *args: target(*args)
    )

    await async_register_frontend(hass)

    hass.http.async_register_static_paths.assert_awaited_once()
    path_config = hass.http.async_register_static_paths.await_args.args[0][0]
    assert isinstance(path_config, StaticPathConfig)
    assert path_config.url_path == CARD_PATH
    assert Path(path_config.path).is_file()
    assert path_config.cache_headers is True
    hass.data[DATA_EXTRA_MODULE_URL].add.assert_called_once()
    added_url = hass.data[DATA_EXTRA_MODULE_URL].add.call_args.args[0]
    assert added_url.startswith(f"{CARD_PATH}?v=")


async def test_unregister_resource_removes_the_dashboard_resource(
    hass: HomeAssistant,
) -> None:
    """Test unregistering deletes the persisted resource."""
    assert await async_setup_component(hass, "lovelace", {})
    await async_register_frontend(hass)
    assert len(_resource_urls(hass)) == 1

    await async_unregister_resource(hass)

    assert _resource_urls(hass) == []


async def test_card_served_without_config_entry(hass: HomeAssistant) -> None:
    """Test the card is served from component setup, before any entry loads."""
    assert await async_setup_component(hass, DOMAIN, {})

    assert hass.data[STATIC_PATH_REGISTERED] is True


async def test_remove_entry_keeps_resource_while_another_entry_remains(
    hass: HomeAssistant,
) -> None:
    """Test the dashboard resource is only removed with the last entry."""
    assert await async_setup_component(hass, "lovelace", {})
    assert await async_setup_component(hass, DOMAIN, {})
    first = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TARGET_ENTITY_ID: "climate.living_room", "name": "Living Room"},
    )
    second = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TARGET_ENTITY_ID: "climate.bedroom", "name": "Bedroom"},
    )
    first.add_to_hass(hass)
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(first.entry_id)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    assert len(_resource_urls(hass)) == 1

    await hass.config_entries.async_remove(first.entry_id)
    await hass.async_block_till_done()
    assert len(_resource_urls(hass)) == 1

    await hass.config_entries.async_remove(second.entry_id)
    await hass.async_block_till_done()
    assert _resource_urls(hass) == []
