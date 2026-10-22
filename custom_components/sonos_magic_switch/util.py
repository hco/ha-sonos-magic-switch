"""Helpers for looking up Sonos entities."""

from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import SONOS_DOMAIN


@callback
def async_get_sonos_media_players(hass: HomeAssistant) -> list[er.RegistryEntry]:
    """Return the registry entries of all enabled Sonos media players."""
    entity_registry = er.async_get(hass)
    return [
        entity
        for config_entry in hass.config_entries.async_entries(SONOS_DOMAIN)
        for entity in er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
        if entity.domain == MEDIA_PLAYER_DOMAIN and not entity.disabled
    ]
