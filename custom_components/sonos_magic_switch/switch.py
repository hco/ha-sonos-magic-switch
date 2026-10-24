"""Module providing the Sonos Magic Switch platform."""

from typing import Any

from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    MediaPlayerState,
)
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_PICTURE, STATE_UNAVAILABLE
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import LOGGER
from .util import (
    MediaPlayerAction,
    async_find_largest_playing_group_leader,
    async_get_sonos_media_players,
    async_get_turn_off_action,
    async_get_turn_on_action,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Sonos Magic Switch platform."""
    device_registry = dr.async_get(hass)

    LOGGER.debug("Setting up for config entry '%s'", config_entry.entry_id)

    async_add_entities(
        SonosMagicSwitch(device, media_player)
        for media_player in async_get_sonos_media_players(hass)
        if media_player.device_id
        if (device := device_registry.async_get(media_player.device_id))
    )


class SonosMagicSwitch(SwitchEntity):
    """Switch that joins the playing Sonos group, or starts playing."""

    _attr_has_entity_name = True
    _attr_translation_key = "magic_switch"
    _attr_should_poll = False
    # The cover changes with every song, like it does for the media players
    _unrecorded_attributes = frozenset({ATTR_ENTITY_PICTURE})

    def __init__(
        self, device: dr.AnyDeviceEntry, media_player: er.RegistryEntry
    ) -> None:
        """Initialize the Sonos Magic Switch."""
        # Link to the Sonos device instead of claiming it via device_info, which
        # would create a duplicate device owned by this integration
        self.device_entry = device
        self._media_player_entity_id = media_player.entity_id
        self._attr_unique_id = media_player.unique_id

    async def async_added_to_hass(self) -> None:
        """Follow the state of all Sonos players, which the cover depends on."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [
                    media_player.entity_id
                    for media_player in async_get_sonos_media_players(self.hass)
                ],
                self._async_sonos_state_changed,
            )
        )
        self._async_update_from_sonos()

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Keep the switch in place when its entity_id is changed."""
        # Nothing set up in async_added_to_hass depends on the own entity_id

    @callback
    def _async_sonos_state_changed(self, event: Event[EventStateChangedData]) -> None:
        self._async_update_from_sonos()
        self.async_write_ha_state()

    @callback
    def _async_update_from_sonos(self) -> None:
        state = self.hass.states.get(self._media_player_entity_id)
        self._attr_available = state is not None and state.state != STATE_UNAVAILABLE
        self._attr_is_on = state is not None and state.state == MediaPlayerState.PLAYING
        self._attr_entity_picture = self._async_find_entity_picture(state)

    @callback
    def _async_find_entity_picture(self, state: State | None) -> str | None:
        """Return the cover of what is playing, or would play when turned on."""
        if not self._attr_available:
            return None
        if not self._attr_is_on and (
            group_leader := async_find_largest_playing_group_leader(
                self.hass, self._media_player_entity_id
            )
        ):
            state = self.hass.states.get(group_leader)
        return state.attributes.get(ATTR_ENTITY_PICTURE) if state else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Join the largest playing group, or start playing if there is none."""
        await self._async_call_media_player_action(
            async_get_turn_on_action(self.hass, self._media_player_entity_id)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Pause if the media player is alone, otherwise leave the group."""
        if action := async_get_turn_off_action(self.hass, self._media_player_entity_id):
            await self._async_call_media_player_action(action)

    async def _async_call_media_player_action(self, action: MediaPlayerAction) -> None:
        await self.hass.services.async_call(
            MEDIA_PLAYER_DOMAIN, action.service, action.data, blocking=True
        )
