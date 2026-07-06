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
    
    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    return True