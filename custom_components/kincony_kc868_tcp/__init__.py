"""Kincony SHA base setup."""

from __future__ import annotations

import logging
import re
import socket
import threading
import time
import contextlib
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DEFAULT_PORT, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


class KTransport:
    """Basic TCP transport with a shared socket and lock."""

    def __init__(self, host: str, port: int) -> None:
        self.address = (host, port)
        self.lock = threading.Lock()
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(5)
        self.connected = False

    def _send(self, command: str) -> None:
        self.s.sendall(command.encode())

    def _read(self) -> str:
        return self.s.recv(1024).decode("utf-8")

    def getLock(self) -> threading.Lock:
        return self.lock

    def call(self, command: str) -> str:
        if not self.connected:
            try:
                self.s.connect(self.address)
                self.connected = True
            except Exception as exc:
                raise ConnectionError("Cannot connect socket") from exc

        try:
            self._send(command)
        except BrokenPipeError:
            with contextlib.suppress(OSError):
                self.s.close()
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(5)
            self.connected = False
            time.sleep(1)
            return self.call(command)

        try:
            result = self._read()
        except Exception as exc:
            with contextlib.suppress(OSError):
                self.s.close()
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(5)
            self.connected = False
            raise ConnectionError("Socket read error") from exc

        return result

    def close(self) -> None:
        with self.lock:
            with contextlib.suppress(OSError):
                self.s.close()
            self.connected = False


class KConnection:
    """High-level Kincony commands for a given relay index."""

    def __init__(self, s: KTransport, index: str) -> None:
        self.s = s
        self.index = index

    def send2K(self, action_type: str) -> str:
        kcode = "255"

        if action_type == "on" and self.index == "all":
            command = "RELAY-SET_ALL-" + kcode + ",255"
        elif action_type == "off" and self.index == "all":
            command = "RELAY-SET_ALL-" + kcode + ",0"
        elif action_type == "on":
            command = "RELAY-SET-" + kcode + "," + self.index + ",1"
        elif action_type == "off":
            command = "RELAY-SET-" + kcode + "," + self.index + ",0"
        elif action_type == "get":
            command = "RELAY-READ-" + kcode + "," + self.index
        elif action_type == "test":
            command = "RELAY-TEST-NOW"
        elif action_type == "scan":
            command = "RELAY-SCAN_DEVICE-NOW"
        else:
            command = "zzz"

        result = self.s.call(command)
        _LOGGER.debug("request:%s response:%s", command, result)
        return result

    def send2KWithLock(self, action_type: str) -> str:
        with self.s.getLock():
            result = self.send2K(action_type)
        return result

    def turnOn(self) -> None:
        result = self.send2KWithLock("on")
        x = re.match(r"RELAY-SET-\d+,\d+,(\d+),OK", result)
        if not x or x.group(1) != "1":
            _LOGGER.warning("Unexpected turn on response for %s: %s", self.index, result)

    def turnOff(self) -> None:
        result = self.send2KWithLock("off")
        x = re.match(r"RELAY-SET-\d+,\d+,(\d+),OK", result)
        if not x or x.group(1) != "0":
            _LOGGER.warning("Unexpected turn off response for %s: %s", self.index, result)

    def getStatus(self) -> bool:
        result = self.send2KWithLock("get")
        x = re.match(r"RELAY-READ-\d+,\d+,(\d+),OK", result)
        if not x:
            raise ValueError(f"Cannot parse status for {self.index}: {result}")
        return x.group(1) == "1"


class KinconyClient:
    """Helper that wraps Kincony calls on the executor."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        self._hass = hass
        self.host = host
        self.port = port
        self._transport = KTransport(host, port)

    async def async_turn_on(self, channel: int) -> None:
        connection = KConnection(self._transport, str(channel))
        await self._hass.async_add_executor_job(connection.turnOn)

    async def async_turn_off(self, channel: int) -> None:
        connection = KConnection(self._transport, str(channel))
        await self._hass.async_add_executor_job(connection.turnOff)

    async def async_get_status(self, channel: int) -> bool:
        connection = KConnection(self._transport, str(channel))
        return await self._hass.async_add_executor_job(connection.getStatus)

    async def async_ping(self) -> None:
        connection = KConnection(self._transport, "1")
        await self._hass.async_add_executor_job(connection.send2KWithLock, "test")

    async def async_get_channel_count(self) -> int | None:
        """Try to read channel count via scan command."""

        def _scan() -> int | None:
            connection = KConnection(self._transport, "1")
            result = connection.send2KWithLock("scan")
            match = re.match(r"RELAY-SCAN_DEVICE-CHANNEL_(\d+),OK", result)
            if match:
                return int(match.group(1))
            return None

        return await self._hass.async_add_executor_job(_scan)

    def close(self) -> None:
        """Close the underlying transport."""
        self._transport.close()


async def async_setup(hass: HomeAssistant, _config: dict[str, Any]) -> bool:
    """Set up the Kincony integration (config entries only)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kincony from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    client = KinconyClient(hass, host, port)

    try:
        await client.async_ping()
    except Exception as exc:
        raise ConfigEntryNotReady from exc

    hass.data[DOMAIN][entry.entry_id] = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    client: KinconyClient | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        if client:
            client.close()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
