"""Config flow for Kincony SHA."""

from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.config_entries import ConfigEntry

from . import KinconyClient
from .const import CONF_CHANNEL_COUNT, DEFAULT_CHANNEL_COUNT, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


class KinconyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kincony SHA."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            try:
                info = await async_validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured(updates=user_input)
                return self.async_create_entry(
                    title=user_input[CONF_HOST],
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_CHANNEL_COUNT: info.get(CONF_CHANNEL_COUNT, DEFAULT_CHANNEL_COUNT),
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_import(self, user_input: dict) -> FlowResult:
        """Handle import from YAML."""
        return await self.async_step_user(user_input)



async def async_validate_input(
    hass: HomeAssistant, data: dict[str, str | int]
) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    host: str = data[CONF_HOST]
    port: int = int(data[CONF_PORT])
    client = KinconyClient(hass, host, port)

    channel_count: int | None = None
    try:
        channel_count = await client.async_get_channel_count()
    except Exception as exc:
        _LOGGER.debug("Channel scan failed, falling back to ping: %s", exc)
        try:
            await client.async_ping()
        except Exception as exc2:
            raise CannotConnect from exc2

    if channel_count is None:
        channel_count = DEFAULT_CHANNEL_COUNT

    return {"title": host, CONF_CHANNEL_COUNT: channel_count}


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class KinconyOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to tweak relay exposure."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_CHANNEL_COUNT: user_input[CONF_CHANNEL_COUNT],
                },
            )

        current_count = self.config_entry.options.get(
            CONF_CHANNEL_COUNT,
            self.config_entry.data.get(CONF_CHANNEL_COUNT, DEFAULT_CHANNEL_COUNT),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHANNEL_COUNT, default=current_count): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=32)
                    ),
                }
            ),
        )


async def async_get_options_flow(config_entry: ConfigEntry):
    """Return the options flow handler."""
    return KinconyOptionsFlowHandler(config_entry)
