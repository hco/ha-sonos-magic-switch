"""The Sonos Magic Switch integration."""

from collections import defaultdict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.helper_integration import async_remove_helper_devices

from .const import LOGGER, SONOS_DOMAIN

PLATFORMS: list[Platform] = [Platform.SWITCH]

LEGACY_UNIQUE_ID_SUFFIX = "_sonos_magic_switch"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sonos Magic Switch from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


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
