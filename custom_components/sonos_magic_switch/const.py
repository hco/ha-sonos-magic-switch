"""Constants for the Sonos Magic Switch integration."""

from logging import Logger, getLogger

DOMAIN = "sonos_magic_switch"
SONOS_DOMAIN = "sonos"
LOGGER: Logger = getLogger(__package__)

CONF_VOLUME_PER_ROOM = "volume_per_room"
# Volume in percent a room starts out with once it sets or limits its volume
DEFAULT_VOLUME = 25.0
