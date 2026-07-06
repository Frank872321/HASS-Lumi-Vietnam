from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN

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
    return True