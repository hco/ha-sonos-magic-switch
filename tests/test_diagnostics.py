"""Tests for the Sonos Magic Switch diagnostics."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    add_sonos_player,
    config_entry: MockConfigEntry,
) -> None:
    """The diagnostics show the players and what the switches would do."""
    add_sonos_player("RINCON_1", "Kitchen")
    add_sonos_player("RINCON_2", "Living Room")
    hass.states.async_set(
        "media_player.kitchen",
        "paused",
        {"group_members": ["media_player.kitchen"], "media_title": "Private"},
    )
    hass.states.async_set(
        "media_player.living_room",
        "playing",
        {
            "group_members": ["media_player.living_room"],
            "source": "TV",
            "entity_picture": "/api/media_player_proxy/living_room?token=secret",
        },
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, config_entry
    )

    assert diagnostics == {
        "media_players": {
            "media_player.kitchen": {
                "unique_id": "RINCON_1",
                "disabled_by": None,
                "state": "paused",
                "group_members": ["media_player.kitchen"],
                "source": None,
                "entity_picture": None,
            },
            "media_player.living_room": {
                "unique_id": "RINCON_2",
                "disabled_by": None,
                "state": "playing",
                "group_members": ["media_player.living_room"],
                "source": "TV",
                "entity_picture": "**REDACTED**",
            },
        },
        "switches": {
            "switch.kitchen_magic_switch": {
                "unique_id": "RINCON_1",
                "disabled_by": None,
                "media_player": "media_player.kitchen",
                "state": "off",
                "entity_picture": "**REDACTED**",
                "turn_on": {
                    "service": "join",
                    "data": {
                        "entity_id": "media_player.living_room",
                        "group_members": ["media_player.kitchen"],
                    },
                },
                "turn_off": {
                    "service": "media_pause",
                    "data": {"entity_id": "media_player.kitchen"},
                },
            },
            "switch.living_room_magic_switch": {
                "unique_id": "RINCON_2",
                "disabled_by": None,
                "media_player": "media_player.living_room",
                "state": "on",
                "entity_picture": "**REDACTED**",
                "turn_on": {
                    "service": "media_play",
                    "data": {"entity_id": "media_player.living_room"},
                },
                "turn_off": {
                    "service": "media_pause",
                    "data": {"entity_id": "media_player.living_room"},
                },
            },
        },
    }
