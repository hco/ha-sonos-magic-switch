"""Tests for the Sonos Magic Switch platform."""

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

KITCHEN = "media_player.kitchen"
LIVING_ROOM = "media_player.living_room"
BATH = "media_player.bath"
KITCHEN_SWITCH = "switch.kitchen_magic_switch"


@pytest.fixture(autouse=True)
async def setup_integration(
    hass: HomeAssistant, add_sonos_player, config_entry: MockConfigEntry
) -> None:
    """Set up three Sonos players and the integration."""
    add_sonos_player("RINCON_1", "Kitchen")
    add_sonos_player("RINCON_2", "Living Room")
    add_sonos_player("RINCON_3", "Bath")
    for entity_id in (KITCHEN, LIVING_ROOM, BATH):
        _set_player(hass, entity_id, "paused")

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


def _set_player(
    hass: HomeAssistant,
    entity_id: str,
    state: str,
    group: list[str] | None = None,
    picture: str | None = None,
) -> None:
    attributes = {"group_members": group or [entity_id]}
    if picture:
        attributes["entity_picture"] = picture
    hass.states.async_set(entity_id, state, attributes)


def _switch_picture(hass: HomeAssistant) -> str | None:
    return hass.states.get(KITCHEN_SWITCH).attributes.get("entity_picture")


async def _call_switch(hass: HomeAssistant, service: str) -> None:
    await hass.services.async_call(
        "switch", service, {"entity_id": KITCHEN_SWITCH}, blocking=True
    )


async def test_switch_is_linked_to_sonos_device(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """The switch is named after and attached to the Sonos device."""
    switch = entity_registry.async_get(KITCHEN_SWITCH)
    media_player = entity_registry.async_get(KITCHEN)

    assert switch.unique_id == "RINCON_1"
    assert switch.device_id == media_player.device_id
    assert hass.states.get(KITCHEN_SWITCH).name == "Kitchen Magic Switch"


async def test_state_follows_media_player(hass: HomeAssistant) -> None:
    """The switch is on while the media player is playing."""
    assert hass.states.get(KITCHEN_SWITCH).state == STATE_OFF

    _set_player(hass, KITCHEN, "playing")
    await hass.async_block_till_done()
    assert hass.states.get(KITCHEN_SWITCH).state == STATE_ON

    hass.states.async_set(KITCHEN, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert hass.states.get(KITCHEN_SWITCH).state == STATE_UNAVAILABLE


async def test_turn_on_starts_playing_without_playing_group(
    hass: HomeAssistant,
) -> None:
    """Without anything playing elsewhere, the player itself starts playing."""
    calls = async_mock_service(hass, "media_player", "media_play")

    await _call_switch(hass, "turn_on")

    assert len(calls) == 1
    assert calls[0].data == {"entity_id": KITCHEN}


async def test_turn_on_joins_largest_playing_group(hass: HomeAssistant) -> None:
    """The player joins the leader of the largest playing group."""
    calls = async_mock_service(hass, "media_player", "join")
    group = [LIVING_ROOM, BATH]
    _set_player(hass, BATH, "playing", group)
    _set_player(hass, LIVING_ROOM, "playing", group)
    await hass.async_block_till_done()

    await _call_switch(hass, "turn_on")

    assert len(calls) == 1
    assert calls[0].data == {"entity_id": LIVING_ROOM, "group_members": [KITCHEN]}


async def test_turn_on_ignores_own_group(hass: HomeAssistant) -> None:
    """The player does not try to join itself."""
    play_calls = async_mock_service(hass, "media_player", "media_play")
    join_calls = async_mock_service(hass, "media_player", "join")
    _set_player(hass, KITCHEN, "playing")
    await hass.async_block_till_done()

    await _call_switch(hass, "turn_on")

    assert join_calls == []
    assert len(play_calls) == 1


async def test_turn_off_pauses_single_player(hass: HomeAssistant) -> None:
    """A player that is not grouped is paused."""
    calls = async_mock_service(hass, "media_player", "media_pause")
    _set_player(hass, KITCHEN, "playing")
    await hass.async_block_till_done()

    await _call_switch(hass, "turn_off")

    assert len(calls) == 1
    assert calls[0].data == {"entity_id": KITCHEN}


async def test_turn_off_leaves_group(hass: HomeAssistant) -> None:
    """A grouped player leaves the group."""
    calls = async_mock_service(hass, "media_player", "unjoin")
    _set_player(hass, KITCHEN, "playing", [LIVING_ROOM, KITCHEN])
    await hass.async_block_till_done()

    await _call_switch(hass, "turn_off")

    assert len(calls) == 1
    assert calls[0].data == {"entity_id": KITCHEN}


async def test_turn_off_without_group_members_attribute(hass: HomeAssistant) -> None:
    """A player without group information is paused."""
    calls = async_mock_service(hass, "media_player", "media_pause")
    hass.states.async_set(KITCHEN, "playing")
    await hass.async_block_till_done()

    await _call_switch(hass, "turn_off")

    assert len(calls) == 1


async def test_picture_of_playing_player(hass: HomeAssistant) -> None:
    """A playing switch shows the cover of its own player."""
    _set_player(hass, LIVING_ROOM, "playing", picture="/living_room.jpg")
    _set_player(hass, KITCHEN, "playing", picture="/kitchen.jpg")
    await hass.async_block_till_done()

    assert _switch_picture(hass) == "/kitchen.jpg"


async def test_picture_of_group_to_join(hass: HomeAssistant) -> None:
    """A switch that would join a group shows and follows the group's cover."""
    _set_player(hass, KITCHEN, "paused", picture="/kitchen.jpg")
    group = [LIVING_ROOM, BATH]
    _set_player(hass, BATH, "playing", group, picture="/bath.jpg")
    _set_player(hass, LIVING_ROOM, "playing", group, picture="/song_1.jpg")
    await hass.async_block_till_done()
    assert _switch_picture(hass) == "/song_1.jpg"

    _set_player(hass, LIVING_ROOM, "playing", group, picture="/song_2.jpg")
    await hass.async_block_till_done()
    assert _switch_picture(hass) == "/song_2.jpg"

    hass.states.async_set(KITCHEN, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert _switch_picture(hass) is None


async def test_picture_of_paused_player(hass: HomeAssistant) -> None:
    """Without a group to join, the switch shows what it would resume."""
    _set_player(hass, KITCHEN, "paused", picture="/kitchen.jpg")
    await hass.async_block_till_done()
    assert _switch_picture(hass) == "/kitchen.jpg"

    _set_player(hass, KITCHEN, "paused")
    await hass.async_block_till_done()
    assert _switch_picture(hass) is None


async def test_picture_is_not_recorded(hass: HomeAssistant) -> None:
    """The cover is left out of the history, like for the media players."""
    state = hass.states.get(KITCHEN_SWITCH)

    assert "entity_picture" in state.state_info["unrecorded_attributes"]
