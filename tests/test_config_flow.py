"""Tests for the Sonos Magic Switch config flow."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sonos_magic_switch.const import CONF_VOLUME_PER_ROOM, DOMAIN


async def test_user_flow(hass: HomeAssistant, add_sonos_player) -> None:
    """The flow creates an entry after confirmation."""
    add_sonos_player("RINCON_1", "Kitchen")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Sonos Magic Switch"


async def test_user_flow_without_sonos_players(hass: HomeAssistant) -> None:
    """The flow aborts if there are no Sonos players."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_single_instance(
    hass: HomeAssistant, add_sonos_player, config_entry: MockConfigEntry
) -> None:
    """Only one entry can be configured."""
    add_sonos_player("RINCON_1", "Kitchen")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow(
    hass: HomeAssistant, add_sonos_player, config_entry: MockConfigEntry
) -> None:
    """The options flow turns the volume settings per room on."""
    add_sonos_player("RINCON_1", "Kitchen")
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_VOLUME_PER_ROOM: True}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_VOLUME_PER_ROOM: True}
    assert hass.states.get("number.kitchen_magic_switch_volume")
