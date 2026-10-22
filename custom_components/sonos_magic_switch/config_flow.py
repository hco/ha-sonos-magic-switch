"""Config flow for Sonos Magic Switch."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow, device_registry as dr

from .const import DOMAIN


async def _async_has_devices(hass: HomeAssistant) -> bool:
    """Return if there are devices that can be discovered."""
    device_registry = dr.async_get(hass)

    sonos_devices = [
        device
        for device in device_registry.devices.values()
        if any(identifier[0] == "sonos" for identifier in device.identifiers)
    ]

    return len(sonos_devices) > 0


config_entry_flow.register_discovery_flow(
    DOMAIN, "Sonos Magic Switch", _async_has_devices
)
