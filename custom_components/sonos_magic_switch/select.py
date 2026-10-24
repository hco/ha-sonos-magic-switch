"""Whether a room's Sonos Magic Switch sets or limits its volume."""

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_VOLUME_PER_ROOM
from .entity import SonosMagicSwitchEntity
from .util import (
    SonosMagicSwitchConfigEntry,
    VolumeMode,
    VolumeSetting,
    async_get_sonos_devices,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: SonosMagicSwitchConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the volume mode of every room, if the volume is set per room."""
    if not config_entry.options.get(CONF_VOLUME_PER_ROOM):
        return

    async_add_entities(
        SonosMagicSwitchVolumeMode(
            device,
            media_player,
            config_entry.runtime_data.setdefault(
                media_player.unique_id, VolumeSetting()
            ),
        )
        for media_player, device in async_get_sonos_devices(hass)
    )


class SonosMagicSwitchVolumeMode(SonosMagicSwitchEntity, SelectEntity, RestoreEntity):
    """Whether the switch keeps, sets or limits the volume of the room."""

    _attr_translation_key = "volume_mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = [mode.value for mode in VolumeMode]

    def __init__(
        self,
        device: dr.AnyDeviceEntry,
        media_player: er.RegistryEntry,
        volume_setting: VolumeSetting,
    ) -> None:
        """Initialize the volume mode of the room."""
        super().__init__(device, media_player)
        self._volume_setting = volume_setting

    async def async_added_to_hass(self) -> None:
        """Restore the volume mode."""
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) and state.state in self.options:
            self._volume_setting.mode = VolumeMode(state.state)

    @property
    def current_option(self) -> str:
        """Return the volume mode."""
        return self._volume_setting.mode

    async def async_select_option(self, option: str) -> None:
        """Change the volume mode."""
        self._volume_setting.mode = VolumeMode(option)
        self.async_write_ha_state()
