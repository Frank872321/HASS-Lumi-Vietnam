from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from . import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True