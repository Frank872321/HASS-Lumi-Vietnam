from __future__ import annotations

import logging
from uuid import uuid4

import paho.mqtt.client as mqtt

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = []  # add e.g. ["sensor", "switch"] as you build them

type LumiConfigEntry = ConfigEntry["LumiGateway"]


def _signal(entry_id: str, topic: str) -> str:
    return f"{DOMAIN}_{entry_id}_{topic}"


class LumiGateway:
    """Owns one paho client per config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.client: mqtt.Client | None = None
        self.last_payloads: dict[str, str] = {}

    async def async_start(self) -> None:
        def _create() -> mqtt.Client:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"ha-lumi-{uuid4().hex[:8]}",
            )
            data = self.entry.data
            if data.get("username"):
                client.username_pw_set(data["username"], data.get("password"))
            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            client.reconnect_delay_set(min_delay=5, max_delay=120)
            client.connect_async(data["host"], data["port"], keepalive=60)
            client.loop_start()
            return client

        self.client = await self.hass.async_add_executor_job(_create)

    async def async_stop(self) -> None:
        def _stop() -> None:
            if self.client is None:
                return
            self.client.loop_stop()
            self.client.disconnect()

        await self.hass.async_add_executor_job(_stop)
        self.client = None

    # --- paho callbacks: these run on paho's network thread ---

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.is_failure:
            _LOGGER.warning("Lumi %s: connect refused: %s", self.entry.title, reason_code)
            return
        _LOGGER.debug("Lumi %s: connected", self.entry.title)
        # Replace with the actual prefix once you know the topic schema.
        client.subscribe("#", qos=0)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        _LOGGER.debug("Lumi %s: disconnected (%s)", self.entry.title, reason_code)

    def _on_message(
        self, client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage
    ) -> None:
        payload = msg.payload.decode(errors="replace")
        self.last_payloads[msg.topic] = payload
        # Marshal onto the HA event loop - this thread is NOT the loop.
        self.hass.loop.call_soon_threadsafe(
            async_dispatcher_send,
            self.hass,
            _signal(self.entry.entry_id, msg.topic),
            payload,
        )

    @callback
    def subscribe(self, callback_fn):
        """Helper for platforms to register a dispatcher listener."""
        from homeassistant.helpers.dispatcher import async_dispatcher_connect

        return async_dispatcher_connect(
            self.hass,
            _signal(self.entry.entry_id, "#"),  # placeholder
            callback_fn,
        )


async def async_setup_entry(hass: HomeAssistant, entry: LumiConfigEntry) -> bool:
    gateway = LumiGateway(hass, entry)
    await gateway.async_start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = gateway
    entry.runtime_data = gateway

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LumiConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok