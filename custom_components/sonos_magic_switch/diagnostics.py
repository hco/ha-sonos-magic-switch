"""Diagnostics for Sonos Magic Switch."""

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.components.media_player import ATTR_INPUT_SOURCE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_PICTURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .util import (
    async_get_sonos_media_players,
    async_get_turn_off_action,
    async_get_turn_on_action,
    group_members,
)

# The picture links of media players carry an access token
TO_REDACT = {ATTR_ENTITY_PICTURE}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return the Sonos players and what the switches would do with them."""
    media_players = async_get_sonos_media_players(hass, include_disabled=True)
    media_players_by_unique_id = {
        media_player.unique_id: media_player for media_player in media_players
    }

    diagnostics: dict[str, Any] = {"media_players": {}, "switches": {}}

    for media_player in media_players:
        state = hass.states.get(media_player.entity_id)
        diagnostics["media_players"][media_player.entity_id] = {
            "unique_id": media_player.unique_id,
            "disabled_by": media_player.disabled_by,
            "state": state.state if state else None,
            "group_members": group_members(state) if state else None,
            "source": state.attributes.get(ATTR_INPUT_SOURCE) if state else None,
            "entity_picture": (
                state.attributes.get(ATTR_ENTITY_PICTURE) if state else None
            ),
        }

    for switch in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        state = hass.states.get(switch.entity_id)
        media_player = media_players_by_unique_id.get(switch.unique_id)
        turn_on = turn_off = None
        if media_player:
            turn_on = async_get_turn_on_action(hass, media_player.entity_id)
            turn_off = async_get_turn_off_action(hass, media_player.entity_id)
        diagnostics["switches"][switch.entity_id] = {
            "unique_id": switch.unique_id,
            "disabled_by": switch.disabled_by,
            "media_player": media_player.entity_id if media_player else None,
            "state": state.state if state else None,
            "entity_picture": (
                state.attributes.get(ATTR_ENTITY_PICTURE) if state else None
            ),
            "turn_on": asdict(turn_on) if turn_on else None,
            "turn_off": asdict(turn_off) if turn_off else None,
        }

    return async_redact_data(diagnostics, TO_REDACT)
