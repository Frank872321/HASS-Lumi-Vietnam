import json
import logging
from uuid import uuid4

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[str] = ["switch"]  # add sensor etc. as you support them


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_send_command(hass: HomeAssistant, objects: list[dict]) -> None:
    """Publish a set command to the HC. `objects` is the "objects" array."""
    reqid = uuid4().hex[:15]
    payload = {
        "cmd": "set",
        "control_source": {
            "id": "homeassistant",
            "previous_control_reqid": "",
            "type": "app",
        },
        "objects": objects,
        "reqid": reqid,
        "source": "core",
        "timestamp": 0,  # confirmed ignored by the HC
    }
    await mqtt.async_publish(
        hass, "component/hc-zb/control", json.dumps(payload), qos=0, retain=False
    )