"""Volume a room is turned on with by its Sonos Magic Switch."""

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_VOLUME_PER_ROOM
from .entity import SonosMagicSwitchEntity
from .util import SonosMagicSwitchConfigEntry, VolumeSetting, async_get_sonos_devices


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: SonosMagicSwitchConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the volume of every room, if the volume is set per room."""
    if not config_entry.options.get(CONF_VOLUME_PER_ROOM):
        return

    async_add_entities(
        SonosMagicSwitchVolume(
            device,
            media_player,
            config_entry.runtime_data.setdefault(
                media_player.unique_id, VolumeSetting()
            ),
        )
        for media_player, device in async_get_sonos_devices(hass)
    )


class SonosMagicSwitchVolume(SonosMagicSwitchEntity, RestoreNumber):
    """Volume the switch sets or limits the room to."""

    _attr_translation_key = "volume"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        device: dr.AnyDeviceEntry,
        media_player: er.RegistryEntry,
        volume_setting: VolumeSetting,
    ) -> None:
        """Initialize the volume of the room."""
        super().__init__(device, media_player)
        self._volume_setting = volume_setting

    async def async_added_to_hass(self) -> None:
        """Restore the volume."""
        await super().async_added_to_hass()
        if (
            data := await self.async_get_last_number_data()
        ) and data.native_value is not None:
            self._volume_setting.level = data.native_value

    @property
    def native_value(self) -> float:
        """Return the volume in percent."""
        return self._volume_setting.level

    async def async_set_native_value(self, value: float) -> None:
        """Change the volume."""
        self._volume_setting.level = value
        self.async_write_ha_state()
