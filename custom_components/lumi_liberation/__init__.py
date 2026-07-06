from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from . import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Set up the domain
    hass.data.setdefault(DOMAIN, {})
    
    # Forward setup to switch.py so HA registers your entities
    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    return True