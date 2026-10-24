"""Tests for setting the volume when a switch is turned on."""

from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall, State
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.sonos_magic_switch.const import CONF_VOLUME_PER_ROOM

KITCHEN = "media_player.kitchen"
LIVING_ROOM = "media_player.living_room"
KITCHEN_SWITCH = "switch.kitchen_magic_switch"
KITCHEN_MODE = "select.kitchen_volume_when_turning_on"
KITCHEN_VOLUME = "number.kitchen_magic_switch_volume"


async def _setup(
    hass: HomeAssistant,
    add_sonos_player,
    config_entry: MockConfigEntry,
    *,
    volume_per_room: bool = True,
) -> None:
    add_sonos_player("RINCON_1", "Kitchen")
    add_sonos_player("RINCON_2", "Living Room")
    _set_player(hass, KITCHEN, "paused", volume=0.5)
    _set_player(hass, LIVING_ROOM, "paused")
    hass.config_entries.async_update_entry(
        config_entry, options={CONF_VOLUME_PER_ROOM: volume_per_room}
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


def _set_player(
    hass: HomeAssistant, entity_id: str, state: str, volume: float = 0.5
) -> None:
    hass.states.async_set(
        entity_id, state, {"group_members": [entity_id], "volume_level": volume}
    )


@pytest.fixture
def media_player_calls(hass: HomeAssistant) -> list[tuple[str, dict[str, Any]]]:
    """Record the media player actions in the order they are called."""
    calls: list[tuple[str, dict[str, Any]]] = []

    async def _record(call: ServiceCall) -> None:
        calls.append((call.service, dict(call.data)))

    for service in ("volume_set", "join", "media_play"):
        hass.services.async_register("media_player", service, _record)
    return calls


async def _configure(hass: HomeAssistant, mode: str, volume: float) -> None:
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": KITCHEN_MODE, "option": mode},
        blocking=True,
    )
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": KITCHEN_VOLUME, "value": volume},
        blocking=True,
    )


async def _turn_on(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": KITCHEN_SWITCH}, blocking=True
    )


async def test_settings_per_room(
    hass: HomeAssistant, add_sonos_player, config_entry: MockConfigEntry
) -> None:
    """Every room starts out keeping its volume."""
    await _setup(hass, add_sonos_player, config_entry)

    assert hass.states.get(KITCHEN_MODE).state == "keep"
    assert float(hass.states.get(KITCHEN_VOLUME).state) == 25
    assert hass.states.get("select.living_room_volume_when_turning_on")


async def test_no_settings_without_option(
    hass: HomeAssistant, add_sonos_player, config_entry: MockConfigEntry
) -> None:
    """Without the option there are no volume settings."""
    await _setup(hass, add_sonos_player, config_entry, volume_per_room=False)

    assert hass.states.get(KITCHEN_MODE) is None
    assert hass.states.get(KITCHEN_VOLUME) is None


async def test_turning_option_off_removes_settings(
    hass: HomeAssistant,
    add_sonos_player,
    config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Turning the option off removes the volume settings."""
    await _setup(hass, add_sonos_player, config_entry)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_VOLUME_PER_ROOM: False}
    )
    await hass.async_block_till_done()

    assert entity_registry.async_get(KITCHEN_MODE) is None
    assert entity_registry.async_get(KITCHEN_VOLUME) is None
    assert hass.states.get(KITCHEN_MODE) is None
    assert hass.states.get(KITCHEN_VOLUME) is None
    assert hass.states.get(KITCHEN_SWITCH)


async def test_keep_volume(
    hass: HomeAssistant,
    add_sonos_player,
    config_entry: MockConfigEntry,
    media_player_calls: list[tuple[str, dict[str, Any]]],
) -> None:
    """By default the volume is left alone."""
    await _setup(hass, add_sonos_player, config_entry)

    await _turn_on(hass)

    assert media_player_calls == [("media_play", {"entity_id": KITCHEN})]


async def test_set_volume_before_joining(
    hass: HomeAssistant,
    add_sonos_player,
    config_entry: MockConfigEntry,
    media_player_calls: list[tuple[str, dict[str, Any]]],
) -> None:
    """The volume is set before joining, so the room does not start too loud."""
    await _setup(hass, add_sonos_player, config_entry)
    await _configure(hass, "set", 30)
    _set_player(hass, LIVING_ROOM, "playing")
    await hass.async_block_till_done()

    await _turn_on(hass)

    assert media_player_calls == [
        ("volume_set", {"entity_id": KITCHEN, "volume_level": 0.3}),
        ("join", {"entity_id": LIVING_ROOM, "group_members": [KITCHEN]}),
    ]


async def test_set_volume_before_playing(
    hass: HomeAssistant,
    add_sonos_player,
    config_entry: MockConfigEntry,
    media_player_calls: list[tuple[str, dict[str, Any]]],
) -> None:
    """The volume is also set when the room starts playing on its own."""
    await _setup(hass, add_sonos_player, config_entry)
    await _configure(hass, "set", 60)

    await _turn_on(hass)

    assert media_player_calls == [
        ("volume_set", {"entity_id": KITCHEN, "volume_level": 0.6}),
        ("media_play", {"entity_id": KITCHEN}),
    ]


async def test_limit_lowers_louder_volume(
    hass: HomeAssistant,
    add_sonos_player,
    config_entry: MockConfigEntry,
    media_player_calls: list[tuple[str, dict[str, Any]]],
) -> None:
    """A volume above the limit is lowered to it."""
    await _setup(hass, add_sonos_player, config_entry)
    await _configure(hass, "limit", 30)

    await _turn_on(hass)

    assert media_player_calls == [
        ("volume_set", {"entity_id": KITCHEN, "volume_level": 0.3}),
        ("media_play", {"entity_id": KITCHEN}),
    ]


async def test_limit_keeps_quieter_volume(
    hass: HomeAssistant,
    add_sonos_player,
    config_entry: MockConfigEntry,
    media_player_calls: list[tuple[str, dict[str, Any]]],
) -> None:
    """A volume below the limit is kept."""
    await _setup(hass, add_sonos_player, config_entry)
    await _configure(hass, "limit", 60)

    await _turn_on(hass)

    assert media_player_calls == [("media_play", {"entity_id": KITCHEN})]


async def test_settings_are_restored(
    hass: HomeAssistant, add_sonos_player, config_entry: MockConfigEntry
) -> None:
    """The settings survive a restart."""
    mock_restore_cache_with_extra_data(
        hass,
        [
            (State(KITCHEN_MODE, "limit"), {}),
            (
                State(KITCHEN_VOLUME, "40"),
                {
                    "native_value": 40,
                    "native_min_value": 0,
                    "native_max_value": 100,
                    "native_step": 1,
                    "native_unit_of_measurement": "%",
                },
            ),
        ],
    )

    await _setup(hass, add_sonos_player, config_entry)

    assert hass.states.get(KITCHEN_MODE).state == "limit"
    assert float(hass.states.get(KITCHEN_VOLUME).state) == 40


async def test_diagnostics_show_volume(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    add_sonos_player,
    config_entry: MockConfigEntry,
) -> None:
    """The diagnostics show the volume setting and the volume action."""
    await _setup(hass, add_sonos_player, config_entry)
    await _configure(hass, "set", 30)

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, config_entry
    )

    assert diagnostics["options"] == {CONF_VOLUME_PER_ROOM: True}
    switch = diagnostics["switches"][KITCHEN_SWITCH]
    assert switch["volume"] == {"mode": "set", "level": 30}
    assert switch["turn_on"][0] == {
        "service": "volume_set",
        "data": {"entity_id": KITCHEN, "volume_level": 0.3},
    }


async def test_limit_unknown_volume(
    hass: HomeAssistant,
    add_sonos_player,
    config_entry: MockConfigEntry,
    media_player_calls: list[tuple[str, dict[str, Any]]],
) -> None:
    """An unknown volume is limited, so the room cannot start too loud."""
    await _setup(hass, add_sonos_player, config_entry)
    await _configure(hass, "limit", 30)
    hass.states.async_set(KITCHEN, "paused", {"group_members": [KITCHEN]})
    await hass.async_block_till_done()

    await _turn_on(hass)

    assert media_player_calls == [
        ("volume_set", {"entity_id": KITCHEN, "volume_level": 0.3}),
        ("media_play", {"entity_id": KITCHEN}),
    ]
