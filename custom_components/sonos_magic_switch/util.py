"""Helpers for looking up Sonos players and deciding what a switch does."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from homeassistant.components.media_player import (
    ATTR_GROUP_MEMBERS,
    ATTR_MEDIA_VOLUME_LEVEL,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_JOIN,
    SERVICE_UNJOIN,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_VOLUME_SET,
)
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DEFAULT_VOLUME, SONOS_DOMAIN


class VolumeMode(StrEnum):
    """How a room's volume is changed when its switch is turned on."""

    KEEP = "keep"
    SET = "set"
    LIMIT = "limit"


@dataclass
class VolumeSetting:
    """The volume a room is turned on with, shared by its settings entities."""

    mode: VolumeMode = VolumeMode.KEEP
    level: float = DEFAULT_VOLUME


# The volume settings by the unique id of the Sonos media player
type SonosMagicSwitchConfigEntry = ConfigEntry[dict[str, VolumeSetting]]


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
def async_get_sonos_devices(
    hass: HomeAssistant,
) -> list[tuple[er.RegistryEntry, dr.DeviceEntry]]:
    """Return the enabled Sonos media players together with their devices."""
    device_registry = dr.async_get(hass)
    return [
        (media_player, device)
        for media_player in async_get_sonos_media_players(hass)
        if media_player.device_id
        if (device := device_registry.async_get(media_player.device_id))
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
def async_get_turn_on_actions(
    hass: HomeAssistant,
    media_player_entity_id: str,
    volume_setting: VolumeSetting | None,
) -> list[MediaPlayerAction]:
    """Join the largest playing group, or start playing if there is none.

    The volume is changed first, so the room does not start out too loud.
    """
    actions = []
    if volume_action := _async_get_volume_action(
        hass, media_player_entity_id, volume_setting
    ):
        actions.append(volume_action)

    if (
        group_leader := async_find_largest_playing_group_leader(
            hass, media_player_entity_id
        )
    ) is None:
        actions.append(
            MediaPlayerAction(
                SERVICE_MEDIA_PLAY, {ATTR_ENTITY_ID: media_player_entity_id}
            )
        )
    else:
        actions.append(
            MediaPlayerAction(
                SERVICE_JOIN,
                {
                    ATTR_ENTITY_ID: group_leader,
                    ATTR_GROUP_MEMBERS: [media_player_entity_id],
                },
            )
        )
    return actions


@callback
def _async_get_volume_action(
    hass: HomeAssistant,
    media_player_entity_id: str,
    volume_setting: VolumeSetting | None,
) -> MediaPlayerAction | None:
    if volume_setting is None or volume_setting.mode is VolumeMode.KEEP:
        return None

    volume_level = volume_setting.level / 100
    # An unknown volume is limited as well, so the room cannot start too loud
    if volume_setting.mode is VolumeMode.LIMIT and (
        (state := hass.states.get(media_player_entity_id)) is not None
        and (current := state.attributes.get(ATTR_MEDIA_VOLUME_LEVEL)) is not None
        and current <= volume_level
    ):
        return None

    return MediaPlayerAction(
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: media_player_entity_id, ATTR_MEDIA_VOLUME_LEVEL: volume_level},
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
