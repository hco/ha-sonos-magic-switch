"""Helpers for looking up Sonos players and deciding what a switch does."""

from dataclasses import dataclass
from typing import Any

from homeassistant.components.media_player import (
    ATTR_GROUP_MEMBERS,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_JOIN,
    SERVICE_UNJOIN,
    MediaPlayerState,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_MEDIA_PAUSE, SERVICE_MEDIA_PLAY
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers import entity_registry as er

from .const import SONOS_DOMAIN


@dataclass(frozen=True)
class MediaPlayerAction:
    """A media player action that turns a switch on or off."""

    service: str
    data: dict[str, Any]


@callback
def async_get_sonos_media_players(
    hass: HomeAssistant, *, include_disabled: bool = False
) -> list[er.RegistryEntry]:
    """Return the registry entries of the Sonos media players."""
    entity_registry = er.async_get(hass)
    return [
        entity
        for config_entry in hass.config_entries.async_entries(SONOS_DOMAIN)
        for entity in er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
        if entity.domain == MEDIA_PLAYER_DOMAIN
        if include_disabled or not entity.disabled
    ]


@callback
def async_find_largest_playing_group_leader(
    hass: HomeAssistant, media_player_entity_id: str
) -> str | None:
    """Return the leader of the largest playing group the player is not in."""
    playing_groups = [
        group_members(state) or [state.entity_id]
        for media_player in async_get_sonos_media_players(hass)
        if (state := hass.states.get(media_player.entity_id)) is not None
        if state.state == MediaPlayerState.PLAYING
    ]
    other_groups = [
        group for group in playing_groups if media_player_entity_id not in group
    ]

    if not other_groups:
        return None

    # The first group member is the group leader
    return max(other_groups, key=len)[0]


@callback
def async_get_turn_on_action(
    hass: HomeAssistant, media_player_entity_id: str
) -> MediaPlayerAction:
    """Join the largest playing group, or start playing if there is none."""
    if (
        group_leader := async_find_largest_playing_group_leader(
            hass, media_player_entity_id
        )
    ) is None:
        return MediaPlayerAction(
            SERVICE_MEDIA_PLAY, {ATTR_ENTITY_ID: media_player_entity_id}
        )

    return MediaPlayerAction(
        SERVICE_JOIN,
        {ATTR_ENTITY_ID: group_leader, ATTR_GROUP_MEMBERS: [media_player_entity_id]},
    )


@callback
def async_get_turn_off_action(
    hass: HomeAssistant, media_player_entity_id: str
) -> MediaPlayerAction | None:
    """Pause if the player is alone, otherwise leave the group."""
    if (state := hass.states.get(media_player_entity_id)) is None:
        return None

    service = SERVICE_UNJOIN if len(group_members(state)) > 1 else SERVICE_MEDIA_PAUSE

    return MediaPlayerAction(service, {ATTR_ENTITY_ID: media_player_entity_id})


def group_members(state: State) -> list[str]:
    """Return the members of the player's group, the leader first."""
    return state.attributes.get(ATTR_GROUP_MEMBERS) or []
