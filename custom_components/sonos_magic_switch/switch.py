"""Module providing the Sonos Magic Switch platform."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import LOGGER
from .util import async_get_sonos_media_players


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sonos Magic Switch platform."""
    """ print the config_entry object to see what it contains """

    device_registry = dr.async_get(hass)

    LOGGER.debug("Setting up for config entry '%s'", config_entry.entry_id)

    async_add_entities(
        SonosMagicSwitch(device, media_player)
        for media_player in async_get_sonos_media_players(hass)
        if media_player.device_id
        if (device := device_registry.async_get(media_player.device_id))
        if device.name
    )


class SonosMagicSwitch(SwitchEntity):
    """Representation of a Sonos Magic Switch."""

    _media_player_entity_id: str

    def __init__(
        self, device: dr.AnyDeviceEntry, media_player: er.RegistryEntry
    ) -> None:
        """Initialize the Sonos Magic Switch."""
        # Link to the Sonos device instead of claiming it via device_info, which
        # would create a duplicate device owned by this integration
        self.device_entry = device
        self._media_player_entity_id = media_player.entity_id

        self._attr_name = f"{device.name} Magic Switch"
        self._attr_unique_id = media_player.unique_id
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        # Importantly for a push integration, the module that will be getting updates
        # needs to notify HA of changes. The dummy device has a registercallback
        # method, so to this we add the 'self.async_write_ha_state' method, to be
        # called where ever there are changes.
        # The call back registration is done once this entity is registered with HA
        # (rather than in the __init__)
        self.unsub = async_track_state_change_event(
            self.hass, self._media_player_entity_id, self._media_player_state_changed
        )
        self.__update_entity_picture()
        await self._update_state_from_media_player()

    def __get_entity_picture(self) -> str | None:
        if not self._media_player_entity_id:
            return None

        media_player_state = self.hass.states.get(self._media_player_entity_id)

        if (
            media_player_state
            and media_player_state.state == "playing"
            and (entity_picture := media_player_state.attributes.get("entity_picture"))
        ):
            LOGGER.debug(
                "Retrieving entity picture for %s from media player", self.entity_id
            )
            return entity_picture

        largest_group_state = self.__find_largest_group_of_media_players()

        if largest_group_state and (
            entity_picture := self.hass.states.get(
                largest_group_state.entity_id
            ).attributes.get("entity_picture")
        ):
            LOGGER.debug(
                "Retrieving entity picture for %s from largest group", self.entity_id
            )
            return entity_picture

        LOGGER.debug(
            "Did not find a group for %s, setting entity picture to None",
            self.entity_id,
        )

        return None

    def __update_entity_picture(self) -> None:
        # self._attr_entity_picture = self.__get_entity_picture()
        return None

    async def _media_player_state_changed(self, event: Event) -> None:
        self.__update_entity_picture()
        await self._update_state_from_media_player()

    async def _update_state_from_media_player(
        self,
    ) -> None:
        media_player_state = self.hass.states.get(self._media_player_entity_id)
        if not media_player_state:
            return

        self._attr_is_on = media_player_state.state == "playing"
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        if self.unsub:
            self.unsub()

    def turn_on(self) -> None:
        """Join group or start playing if no group exists."""
        if not self._media_player_entity_id:
            return

        largest_group_state = self.__find_largest_group_of_media_players()

        if not largest_group_state:
            self.hass.services.call(
                "media_player",
                "media_play",
                {"entity_id": self._media_player_entity_id},
            )
        else:
            self.hass.services.call(
                "media_player",
                "join",
                {
                    "entity_id": largest_group_state.entity_id,
                    "group_members": [self._media_player_entity_id]
                    + largest_group_state.attributes["group_members"],
                },
            )

    def __find_largest_group_of_media_players(self) -> State | None:
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)

        media_player_states = [
            entity_state
            for entity in entity_registry.entities.values()
            if entity.entity_id.startswith("media_player.")
            if (device_id := entity.device_id)
            if (device := device_registry.async_get(device_id))
            if any(identifier[0] == "sonos" for identifier in device.identifiers)
            if (entity_state := self.hass.states.get(entity.entity_id)) is not None
            if entity_state.state == "playing"
        ]

        if not media_player_states:
            return None

        # sort the media players by the number of group members
        media_player_states.sort(
            key=lambda x: len(x.attributes.get("group_members", [])), reverse=True
        )

        return media_player_states[0]

    def turn_off(self) -> None:
        """If the media player is alone, pause it, otherwise leave group."""
        state = self.hass.states.get(self._media_player_entity_id)
        if not state:
            return

        if state.attributes["group_members"] == [self._media_player_entity_id]:
            self.hass.services.call(
                "media_player",
                "media_pause",
                {"entity_id": self._media_player_entity_id},
            )
        else:
            self.hass.services.call(
                "media_player",
                "unjoin",
                {"entity_id": self._media_player_entity_id},
            )
