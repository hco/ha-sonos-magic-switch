"""The Sonos Magic Switch integration."""

from collections import defaultdict

from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, callback, split_entity_id
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.helper_integration import async_remove_helper_devices

from .const import LOGGER, SONOS_DOMAIN
from .util import async_get_sonos_media_players

PLATFORMS: list[Platform] = [Platform.SWITCH]

LEGACY_UNIQUE_ID_SUFFIX = "_sonos_magic_switch"

# Media player registry changes which add, remove or move a switch
RELOAD_ON_CHANGES = {"entity_id", "device_id", "disabled_by"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sonos Magic Switch from a config entry."""
    _async_follow_media_players(hass, entry)
    # Removed players are no longer in the registry, so remember the Sonos ones
    sonos_entity_ids = {
        media_player.entity_id
        for media_player in async_get_sonos_media_players(hass, include_disabled=True)
    }

    @callback
    def _async_is_sonos_media_player_change(
        event_data: er.EventEntityRegistryUpdatedData,
    ) -> bool:
        if split_entity_id(event_data["entity_id"])[0] != MEDIA_PLAYER_DOMAIN:
            return False
        if event_data["action"] == "remove":
            return event_data["entity_id"] in sonos_entity_ids
        if event_data["action"] == "update" and not (
            RELOAD_ON_CHANGES & event_data["changes"].keys()
        ):
            return False
        entity = er.async_get(hass).async_get(event_data["entity_id"])
        return entity is not None and entity.platform == SONOS_DOMAIN

    @callback
    def _async_reload(_: Event[er.EventEntityRegistryUpdatedData]) -> None:
        hass.config_entries.async_schedule_reload(entry.entry_id)

    # Pick up added, removed, renamed, disabled and re-enabled Sonos players
    entry.async_on_unload(
        hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            _async_reload,
            event_filter=_async_is_sonos_media_player_change,
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


@callback
def _async_follow_media_players(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove or disable switches whose Sonos player was removed or disabled."""
    entity_registry = er.async_get(hass)
    media_players = {
        media_player.unique_id: media_player
        for media_player in async_get_sonos_media_players(hass, include_disabled=True)
    }

    for switch in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if (media_player := media_players.get(switch.unique_id)) is None:
            entity_registry.async_remove(switch.entity_id)
        elif media_player.disabled and not switch.disabled:
            entity_registry.async_update_entity(
                switch.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
            )
            # Unloading left an unavailable placeholder, which Home Assistant only
            # cleans up for removed entities
            hass.states.async_remove(switch.entity_id)
        elif (
            not media_player.disabled
            and switch.disabled_by is er.RegistryEntryDisabler.INTEGRATION
        ):
            entity_registry.async_update_entity(switch.entity_id, disabled_by=None)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an old config entry."""
    if entry.version > 1:
        return False

    if entry.minor_version < 2:
        _async_migrate_to_linked_devices(hass, entry)
        hass.config_entries.async_update_entry(entry, minor_version=2)

    LOGGER.debug(
        "Migrated config entry to version %s.%s", entry.version, entry.minor_version
    )
    return True


@callback
def _async_migrate_to_linked_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Re-key switches by Sonos player and remove the devices this entry owns.

    Switches used to be keyed by the Sonos device id, which changed when Home
    Assistant 2026.8 split devices shared between integrations. Older versions
    could therefore create a second switch for the same player; the oldest one is
    kept so user customizations survive.
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    switches_by_sonos_uid: defaultdict[str, list[er.RegistryEntry]] = defaultdict(list)
    for switch in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        device_id = switch.unique_id.removesuffix(LEGACY_UNIQUE_ID_SUFFIX)
        if (device := device_registry.async_get(device_id)) is None:
            continue
        if sonos_uid := next(
            (value for domain, value in device.identifiers if domain == SONOS_DOMAIN),
            None,
        ):
            switches_by_sonos_uid[sonos_uid].append(switch)

    for sonos_uid, switches in switches_by_sonos_uid.items():
        switches.sort(key=lambda switch: switch.created_at)
        for duplicate in switches[1:]:
            entity_registry.async_remove(duplicate.entity_id)
        entity_registry.async_update_entity(
            switches[0].entity_id, new_unique_id=sonos_uid
        )

    # The switches are linked to the Sonos devices again when they are added
    async_remove_helper_devices(
        hass,
        helper_config_entry_id=entry.entry_id,
        source_device_id=None,
        remove_all_devices=True,
    )
