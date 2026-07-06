from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect, 
    dispatcher_send
)
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
    
    async def mqtt_message_received(msg):
        payload = json.loads(msg.payload)
        
        # PROTCOL PARSING: You need to extract the specific device ID from the broadcast
        # This part depends on how your hub formats the 'status' JSON
        objects = payload.get("objects", []) 
        for obj in objects:
            dev_id = obj.get("hash")  # This is the "zigbee-..." ID
            device_state = obj.get("state") # e.g., {"on": True}
            
            # This is the magic part:
            # Send a signal that ONLY the entity with this specific dev_id will hear
            dispatcher_send(hass, f"{DOMAIN}_update_{dev_id}", device_state)

    await mqtt.async_subscribe(hass, "component/dnet-relay/in/status", mqtt_message_received)
    # Now forward the setup to switch.py
    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    return True