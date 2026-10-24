"""Config flow for Sonos Magic Switch."""

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithReload,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, callback
import voluptuous as vol

from .const import CONF_VOLUME_PER_ROOM, DOMAIN
from .util import async_get_sonos_media_players

OPTIONS_SCHEMA = vol.Schema({vol.Required(CONF_VOLUME_PER_ROOM, default=False): bool})


class SonosMagicSwitchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sonos Magic Switch."""

    VERSION = 1
    # 1.2: switches are linked to the Sonos device instead of owning a copy of it
    MINOR_VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm setup if there are Sonos players to add switches for."""
        if not async_get_sonos_media_players(self.hass):
            return self.async_abort(
                reason="no_devices_found", translation_domain=HOMEASSISTANT_DOMAIN
            )

        if user_input is None:
            self._set_confirm_only()
            return self.async_show_form(step_id="user")

        return self.async_create_entry(title="Sonos Magic Switch", data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return SonosMagicSwitchOptionsFlow()


class SonosMagicSwitchOptionsFlow(OptionsFlowWithReload):
    """Handle the options of Sonos Magic Switch."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose whether the volume is set per room."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
