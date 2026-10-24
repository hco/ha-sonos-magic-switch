"""Base entity for Sonos Magic Switch."""

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import Entity


class SonosMagicSwitchEntity(Entity):
    """Entity that belongs to a Sonos player and is shown on its device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, device: dr.AnyDeviceEntry, media_player: er.RegistryEntry
    ) -> None:
        """Initialize the entity for the Sonos player."""
        # Link to the Sonos device instead of claiming it via device_info, which
        # would create a duplicate device owned by this integration
        self.device_entry = device
        self._media_player_entity_id = media_player.entity_id
        self._attr_unique_id = media_player.unique_id

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Keep the entity in place when its entity_id is changed."""
        # Nothing set up in async_added_to_hass depends on the own entity_id
