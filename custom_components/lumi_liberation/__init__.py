from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN
import json
import logging
from homeassistant.components import mqtt
from homeassistant.helpers.dispatcher import dispatcher_send
from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    # Get the data the user typed in the form
    host = entry.data["Host"]
    port = entry.data["Port"]
    
    # Store it in hass.data so other files can see it
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "host": host,
        "port": port
    }
    
    # Now forward the setup to switch.py
    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    # This is the "Traffic Controller"
    async def status_message_received(msg):
        try:
            payload = json.loads(msg.payload)
            # Based on your status JSON: payload['objects'][0]['data']
            for obj in payload.get("objects", []):
                for device in obj.get("data", []):
                    dev_hash = device.get("hash")
                    state = device.get("states", {}).get("OnOff", {}).get("on")
                    
                    if dev_hash is not None and state is not None:
                        # Shout the news to all switches
                        dispatcher_send(hass, f"{DOMAIN}_state_update_{dev_hash}", state)
        except Exception as e:
            _LOGGER.error(f"Error parsing status: {e}")

    # Subscribe once
    await mqtt.async_subscribe(hass, "component/dnet-relay/in/status", status_message_received)
    
    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    return True
