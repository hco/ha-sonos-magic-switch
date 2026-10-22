"""Config flow for Sonos Magic Switch."""

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN

from .const import DOMAIN
from .util import async_get_sonos_media_players


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
