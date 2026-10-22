"""Fixtures for Sonos Magic Switch tests."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sonos_magic_switch.const import DOMAIN, SONOS_DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the integration from custom_components."""


@pytest.fixture
def sonos_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Add a Sonos config entry, without setting it up."""
    entry = MockConfigEntry(domain=SONOS_DOMAIN)
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def add_sonos_player(
    hass: HomeAssistant,
    sonos_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
):
    """Return a function registering a Sonos player like the Sonos integration."""

    def _add_sonos_player(uid: str, name: str) -> er.RegistryEntry:
        device = device_registry.async_get_or_create(
            config_entry_id=sonos_entry.entry_id,
            identifiers={(SONOS_DOMAIN, uid)},
            name=name,
        )
        return entity_registry.async_get_or_create(
            "media_player",
            SONOS_DOMAIN,
            uid,
            config_entry=sonos_entry,
            device_id=device.id,
            suggested_object_id=name.lower(),
        )

    return _add_sonos_player


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Add a Sonos Magic Switch config entry."""
    entry = MockConfigEntry(domain=DOMAIN, version=1, minor_version=2)
    entry.add_to_hass(hass)
    return entry
