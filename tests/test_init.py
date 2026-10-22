"""Tests for the Sonos Magic Switch setup and migration."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sonos_magic_switch.const import DOMAIN, SONOS_DOMAIN


async def test_migrate_switches_to_sonos_device(
    hass: HomeAssistant,
    add_sonos_player,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Switches are re-keyed, duplicates dropped and linked to the Sonos device."""
    media_player = add_sonos_player("RINCON_1", "Kitchen")
    sonos_device_id = media_player.device_id

    entry = MockConfigEntry(domain=DOMAIN, version=1, minor_version=1)
    entry.add_to_hass(hass)
    # Since HA 2026.8 the Sonos identifiers in device_info created a device owned by
    # this integration
    duplicate_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(SONOS_DOMAIN, "RINCON_1")}
    )
    switch = entity_registry.async_get_or_create(
        "switch",
        DOMAIN,
        f"{sonos_device_id}_sonos_magic_switch",
        config_entry=entry,
        device_id=duplicate_device.id,
        suggested_object_id="kitchen_magic_switch",
    )
    # A later switch for the same player, keyed by another device id
    duplicate_switch = entity_registry.async_get_or_create(
        "switch",
        DOMAIN,
        f"{duplicate_device.id}_sonos_magic_switch",
        config_entry=entry,
        device_id=duplicate_device.id,
        suggested_object_id="kitchen_magic_switch_2",
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.minor_version == 2
    migrated = entity_registry.async_get(switch.entity_id)
    assert migrated.unique_id == "RINCON_1"
    assert migrated.device_id == sonos_device_id
    assert entity_registry.async_get(duplicate_switch.entity_id) is None
    assert dr.async_entries_for_config_entry(device_registry, entry.entry_id) == []
    assert hass.states.get(switch.entity_id) is not None


async def test_unload(
    hass: HomeAssistant, add_sonos_player, config_entry: MockConfigEntry
) -> None:
    """The switches are removed when unloading."""
    add_sonos_player("RINCON_1", "Kitchen")
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("switch.kitchen_magic_switch")

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_new_sonos_player_adds_switch(
    hass: HomeAssistant, add_sonos_player, config_entry: MockConfigEntry
) -> None:
    """A Sonos player added later gets a switch."""
    add_sonos_player("RINCON_1", "Kitchen")
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("switch.bath_magic_switch") is None

    add_sonos_player("RINCON_2", "Bath")
    await hass.async_block_till_done()

    assert hass.states.get("switch.bath_magic_switch") is not None
