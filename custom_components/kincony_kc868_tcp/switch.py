"""Switch platform for Kincony SHA."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KinconyClient
from .const import CONF_CHANNEL_COUNT, DEFAULT_CHANNEL_COUNT, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Kincony switches from a config entry."""
    client: KinconyClient = hass.data[DOMAIN][entry.entry_id]
    channel_count: int = entry.options.get(
        CONF_CHANNEL_COUNT, entry.data.get(CONF_CHANNEL_COUNT, DEFAULT_CHANNEL_COUNT)
    )

    entities = [KinconySwitch(client=client, channel=index) for index in range(1, channel_count + 1)]

    async_add_entities(entities)


class KinconySwitch(SwitchEntity):
    """Representation of a Kincony relay switch."""

    _attr_should_poll = True

    def __init__(self, client: KinconyClient, channel: int) -> None:
        self._client = client
        self._channel = channel
        self._attr_name = f"Relay {channel}"
        self._attr_unique_id = f"{client.host}-relay-{channel}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client.host)},
            name=f"Kincony ({client.host})",
            manufacturer="Kincony",
            model="SHA",
            configuration_url=f"http://{client.host}",
        )
        self._attr_is_on = False
        self._attr_available = True

    async def async_update(self) -> None:
        try:
            self._attr_is_on = await self._client.async_get_status(self._channel)
            self._attr_available = True
        except Exception as err:
            _LOGGER.error(
                "Failed to poll channel %s on %s: %s", self._channel, self._client.host, err
            )
            self._attr_available = False

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self._client.async_turn_on(self._channel)
        except Exception as err:
            self._attr_available = False
            raise HomeAssistantError(f"Failed to turn on channel {self._channel}") from err

        self._attr_is_on = True
        self._attr_available = True

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self._client.async_turn_off(self._channel)
        except Exception as err:
            self._attr_available = False
            raise HomeAssistantError(f"Failed to turn off channel {self._channel}") from err

        self._attr_is_on = False
        self._attr_available = True
