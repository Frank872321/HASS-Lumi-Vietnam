import json
import logging

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, DISCOVERY_SIGNAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"known_devices": set()}

    @callback
    def _handle_status(msg) -> None:
        """Called for every message on the status topic."""
        try:
            payload = json.loads(msg.payload)
        except (ValueError, TypeError):
            return

        for obj in payload.get("objects", []):
            if obj.get("type") != "devices":
                continue
            for dev in obj.get("data", []):
                devid = dev.get("devid")
                if not devid:
                    continue

                known = hass.data[DOMAIN][entry.entry_id]["known_devices"]
                if devid in known:
                    # Existing device — just update its state via a separate signal
                    state = dev.get("states", {}).get("OnOff", {}).get("on")
                    if state is not None:
                        async_dispatcher_send(
                            hass, f"{DOMAIN}_state_update_{devid}", state
                        )
                    continue

                # New device — tell the switch platform to create an entity
                known.add(devid)
                async_dispatcher_send(hass, DISCOVERY_SIGNAL, devid)

    await mqtt.async_subscribe(
        hass, "component/dnet-relay/in/status", _handle_status, qos=0
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok