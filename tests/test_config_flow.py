"""Config flow tests for Kincony KC868 TCP."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kincony_kc868_tcp.config_flow import KinconyOptionsFlowHandler
from custom_components.kincony_kc868_tcp.const import (
    CONF_CHANNEL_COUNT,
    DEFAULT_CHANNEL_COUNT,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


class _FakeClientScan:
    def __init__(self, hass: Any, host: str, port: int) -> None:
        self.host = host
        self.port = port

    async def async_get_channel_count(self) -> int | None:
        return 8

    async def async_ping(self) -> None:
        return None


class _FakeClientFallback:
    def __init__(self, hass: Any, host: str, port: int) -> None:
        self.host = host
        self.port = port

    async def async_get_channel_count(self) -> int | None:
        raise RuntimeError("scan failed")

    async def async_ping(self) -> None:
        return None


@pytest.mark.asyncio
async def test_user_flow_scans_channel_count(hass: Any) -> None:
    """Channel scan succeeds and returns detected count."""
    expected_count = 8
    with patch(
        "custom_components.kincony_kc868_tcp.config_flow.KinconyClient",
        _FakeClientScan,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.2.3.4", CONF_PORT: 4196},
        )
        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["data"][CONF_CHANNEL_COUNT] == expected_count


@pytest.mark.asyncio
async def test_user_flow_falls_back_to_ping(hass: Any) -> None:
    """Falls back to default count when scan fails but ping works."""
    with patch(
        "custom_components.kincony_kc868_tcp.config_flow.KinconyClient",
        _FakeClientFallback,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.2.3.4", CONF_PORT: 4196},
        )
        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["data"][CONF_CHANNEL_COUNT] == DEFAULT_CHANNEL_COUNT


@pytest.mark.asyncio
async def test_options_flow_preserves_detected_default(hass: Any) -> None:
    """Options default uses stored channel count when no override exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_PORT: 4196, CONF_CHANNEL_COUNT: 16},
        options={},
        title="Kincony",
    )
    entry.add_to_hass(hass)

    stored_count = 16
    new_count = 12
    flow = await KinconyOptionsFlowHandler(entry).async_step_init()
    assert flow["type"] == FlowResultType.FORM
    assert flow["data_schema"]({})[CONF_CHANNEL_COUNT] == stored_count

    result2 = await KinconyOptionsFlowHandler(entry).async_step_init(
        user_input={CONF_CHANNEL_COUNT: new_count}
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_CHANNEL_COUNT] == new_count
