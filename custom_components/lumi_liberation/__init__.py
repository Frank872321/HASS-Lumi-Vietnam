from __future__ import annotations

import json
import logging
from uuid import uuid4

import paho.mqtt.client as mqtt

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DISCOVERY_SIGNAL, DOMAIN, TOPIC_STATUS

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch"]

type LumiConfigEntry = ConfigEntry["LumiGateway"]


class LumiGateway:
    """Owns one paho client per config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.client: mqtt.Client | None = None
        self.known_devices: set[str] = set()

    # ---- lifecycle (executor) ----

    async def async_start(self) -> None:
        await self.hass.async_add_executor_job(self._start_client)

    def _start_client(self) -> None:
        data = self.entry.data
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"ha-lumi-{uuid4().hex[:8]}",
        )
        if data.get("username"):
            client.username_pw_set(data["username"], data.get("password"))
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.reconnect_delay_set(min_delay=5, max_delay=120)
        client.connect_async(data["host"], data["port"], keepalive=60)
        client.loop_start()
        self.client = client

    async def async_stop(self) -> None:
        await self.hass.async_add_executor_job(self._stop_client)

    def _stop_client(self) -> None:
        if self.client is None:
            return
        self.client.disconnect()
        self.client.loop_stop()
        self.client = None

    async def async_publish(self, topic: str, payload: str) -> None:
        if self.client is None:
            raise RuntimeError("Lumi gateway client is not running")
        await self.hass.async_add_executor_job(
            self.client.publish, topic, payload, 0, False
        )

    # ---- paho callbacks (run on paho's network thread) ----

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            _LOGGER.warning("Lumi: connect refused (%s)", reason_code)
            return
        _LOGGER.info("Lumi: connected to broker")
        client.subscribe(TOPIC_STATUS, qos=0)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        _LOGGER.info("Lumi: disconnected (%s)", reason_code)

    def _on_message(self, client, userdata, msg) -> None:
        if msg.topic != TOPIC_STATUS:
            return
        try:
            payload = json.loads(msg.payload)
        except (ValueError, TypeError):
            return
        self.hass.loop.call_soon_threadsafe(self._process_status, payload)

    # ---- on the event loop ----

    @callback
    def _process_status(self, payload: dict) -> None:
        for obj in payload.get("objects", []):
            if obj.get("type") != "devices":
                continue
            for dev in obj.get("data", []):
                devid = dev.get("devid")
                if not devid:
                    continue
                if devid not in self.known_devices:
                    self.known_devices.add(devid)
                    async_dispatcher_send(self.hass, DISCOVERY_SIGNAL, devid)
                state = dev.get("states", {}).get("OnOff", {}).get("on")
                if state is not None:
                    async_dispatcher_send(
                        self.hass, f"{DOMAIN}_state_update_{devid}", state
                    )


async def async_setup_entry(hass: HomeAssistant, entry: LumiConfigEntry) -> bool:
    gateway = LumiGateway(hass, entry)
    await gateway.async_start()
    entry.runtime_data = gateway

    # When zeroconf updates host/port on the entry, reload → new client.
    entry.async_on_unload(entry.add_update_listener(_async_restart_on_update))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_restart_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: LumiConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_stop()
    return unload_ok