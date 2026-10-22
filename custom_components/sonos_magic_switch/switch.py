"""Module providing the Sonos Magic Switch platform."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import LOGGER


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sonos Magic Switch platform."""
    """ print the config_entry object to see what it contains """

    device_registry = dr.async_get(hass)

    LOGGER.debug("Setting up for config entry '%s'", config_entry.entry_id)

    # filter all devices that contain a tuple whichs first element is "sonos" in the
    # identifiers and that have a name
    sonos_devices = [
        device
        for device in device_registry.devices.values()
        if any(identifier[0] == "sonos" for identifier in device.identifiers)
        if get_media_player_for_device(hass, device.id) is not None
    ]

    async_add_entities(
        [SonosMagicSwitch(device) for device in sonos_devices if device.name]
    )


def get_media_player_for_device(hass: HomeAssistant, device_id: str) -> State | None:
    """Retrieve the media player entity associated with the given device ID."""
    entity_registry = er.async_get(hass)
    device_entities = er.async_entries_for_device(entity_registry, device_id)

    return next(
        (
            entity
            for entity in device_entities
            if entity.entity_id.startswith("media_player.")
        ),
        None,
    )


class SonosMagicSwitch(SwitchEntity):
    """Representation of a Sonos Magic Switch."""

    _original_device: dr.DeviceEntry
    _media_player_entity_id: str

    def __init__(self, device: dr.DeviceEntry) -> None:
        """Initialize the Sonos Magic Switch."""
        self._original_device = device
        """ abort if the device has no name """
        if not device.name:
            return

        self._attr_name = device.name + " Magic Switch"
        self._attr_unique_id = device.id + "_sonos_magic_switch"
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        # Importantly for a push integration, the module that will be getting updates
        # needs to notify HA of changes. The dummy device has a registercallback
        # method, so to this we add the 'self.async_write_ha_state' method, to be
        # called where ever there are changes.
        # The call back registration is done once this entity is registered with HA
        # (rather than in the __init__)
        self._media_player_entity_id = await self.__get_media_player_entity_id()

        if not self._media_player_entity_id:
            return

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

    async def __get_media_player_entity_id(self) -> str:
        return get_media_player_for_device(
            self.hass, self._original_device.id
        ).entity_id

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

    @property
    def device_info(self) -> dr.DeviceInfo:
        """Return the device info."""
        return dr.DeviceInfo(
            identifiers=self._original_device.identifiers,
        )

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
