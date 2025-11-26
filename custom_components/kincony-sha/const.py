"""Constants for the Kincony SHA integration."""

from homeassistant.const import Platform

DOMAIN = "kincony-sha"
DEFAULT_PORT = 4196
DEFAULT_CHANNEL_COUNT = 32
CONF_CHANNEL_COUNT = "channel_count"

PLATFORMS = [Platform.SWITCH]
