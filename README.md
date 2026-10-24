# Sonos Magic Switch Home Assistant Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

_Home Assistant Integration which adds a magic🪄 switch to SONOS players._

Every Sonos player gets a switch, which is shown on the player's device and is on while the player is playing.

- Turning it **on** will join the largest group of sonos players. If there is no playing group, it will try to start playing on the current player, with the last played source.
- If you turn it **off**, it will leave the group, or stop playing.

The switch shows the album cover of what is playing, or of what would play when it is turned on.

Switches for Sonos players added later are created automatically, and removed or disabled along with their player.

**This integration will set up the following platforms.**

| Platform | Description                                                    |
| -------- | -------------------------------------------------------------- |
| `switch` | Join or leave a sonos group, or start/stop playing             |
| `select` | Whether turning the switch on sets or limits the room's volume |
| `number` | The volume the switch sets or limits the room to               |

## Requirements

- Home Assistant 2026.10 or newer
- The [Sonos integration](https://www.home-assistant.io/integrations/sonos/) set up with at least one player

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hco&repository=ha-sonos-magic-switch&category=integration)

1. Open HACS, click the three dots on the top right and select `Custom repositories`
1. Enter `https://github.com/hco/ha-sonos-magic-switch` as repository, select the type `Integration` and click Add
1. Search for `Sonos Magic Switch`, open it and click Download
1. Restart Home Assistant
1. Go to Settings -> Devices & services, click [Add Integration](https://my.home-assistant.io/redirect/config_flow_start?domain=sonos_magic_switch) and search for `Sonos Magic Switch`

## Configuration is done in the UI

### Volume per room

To keep a room from starting too loud, turn on `Set the volume per room` in the options of the integration. Every Sonos device then gets two settings:

- `Volume when turning on`: `Don't change` (the default), `Set` the volume, or `Limit` it, which only lowers a louder volume. If the current volume is unknown, `Limit` sets it to be safe.
- `Magic Switch volume`: the volume to set or limit to, 25% by default.

The volume is only changed when the room is turned on with its magic switch, and before it joins a group or starts playing. Both settings can be changed by automations, e.g. for a lower limit at night.

## Reporting issues

If a switch joins the wrong group or does nothing, please attach its diagnostics to the [issue](https://github.com/hco/ha-sonos-magic-switch/issues): go to Settings -> Devices & services -> Sonos Magic Switch, open the three dots menu and select `Download diagnostics`. They show the Sonos players and what turning each switch on or off would do.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/hco/ha-sonos-magic-switch.svg?style=for-the-badge
[commits]: https://github.com/hco/ha-sonos-magic-switch/commits/main
[license-shield]: https://img.shields.io/github/license/hco/ha-sonos-magic-switch.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/hco/ha-sonos-magic-switch.svg?style=for-the-badge
[releases]: https://github.com/hco/ha-sonos-magic-switch/releases
