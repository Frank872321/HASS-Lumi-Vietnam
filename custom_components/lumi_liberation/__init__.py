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
    # 1. Setup Data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"host": entry.data["Host"], "port": entry.data["Port"]}
    
    # 2. The Traffic Controller
    async def status_message_received(msg):
        try:
            payload = json.loads(msg.payload)
            for obj in payload.get("objects", []):
                for device in obj.get("data", []):
                    dev_hash = device.get("hash")
                    state = device.get("states", {}).get("OnOff", {}).get("on")
                    
                    if dev_hash:
                        # NEW: If the entity doesn't exist, we need to add it 
                        # This triggers your 'add_new_switch' function in switch.py
                        if not hass.data[DOMAIN].get(dev_hash):
                            hass.data[DOMAIN][dev_hash] = True
                            dispatcher_send(hass, DISCOVERY_SIGNAL, dev_hash)
                        
                        # Handle state update
                        if state is not None:
                            dispatcher_send(hass, f"{DOMAIN}_state_update_{dev_hash}", state)
        except Exception as e:
            _LOGGER.error(f"Error parsing status: {e}")

    # 3. Subscribe once
    await mqtt.async_subscribe(hass, "component/dnet-relay/in/status", status_message_received)
    
    # 4. Single setup forward
    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    return True