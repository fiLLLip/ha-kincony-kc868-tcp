"""Switch behavior tests for Kincony KC868 TCP."""

from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.kincony_kc868_tcp import KinconyClient
from custom_components.kincony_kc868_tcp.switch import KinconySwitch

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


class _StubClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.host: str = "stub-host"
        self._fail: bool = fail
        self.turn_on_called: bool = False
        self.turn_off_called: bool = False
        self.status_calls: int = 0

    async def async_get_status(self, channel: int) -> bool:
        self.status_calls += 1
        if self._fail:
            raise RuntimeError("status failed")
        return channel % 2 == 0

    async def async_turn_on(self, channel: int) -> None:
        if self._fail:
            raise RuntimeError("turn on failed")
        self.turn_on_called = True

    async def async_turn_off(self, channel: int) -> None:
        if self._fail:
            raise RuntimeError("turn off failed")
        self.turn_off_called = True


@pytest.mark.asyncio
async def test_update_marks_availability(hass: Any) -> None:
    """Update sets availability based on polling success."""
    client = _StubClient()
    switch = KinconySwitch(cast(KinconyClient, client), channel=2)

    await switch.async_update()
    assert switch.available is True
    assert switch.is_on is True

    client_fail = _StubClient(fail=True)
    switch_fail = KinconySwitch(cast(KinconyClient, client_fail), channel=1)
    await switch_fail.async_update()
    assert switch_fail.available is False


@pytest.mark.asyncio
async def test_turn_on_off_propagate_errors(hass: Any) -> None:
    """Turn on/off handle failures and availability flags."""
    client = _StubClient()
    switch = KinconySwitch(cast(KinconyClient, client), channel=3)

    await switch.async_turn_on()
    assert client.turn_on_called is True
    assert switch.is_on is True
    assert switch.available is True

    await switch.async_turn_off()
    assert client.turn_off_called is True
    assert switch.is_on is False
    assert switch.available is True

    failing_client = _StubClient(fail=True)
    failing_switch = KinconySwitch(cast(KinconyClient, failing_client), channel=4)
    with pytest.raises(HomeAssistantError):
        await failing_switch.async_turn_on()
    assert failing_switch.available is False
