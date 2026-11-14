from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import DOMAIN, DISCOVERY_SIGNAL
import json
import logging
from homeassistant.components import mqtt
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lumi Vietnam from a config entry."""
    # 1. Setup Data (supporting both lowercase and capitalized keys for safety)
    hass.data.setdefault(DOMAIN, {})
    host = entry.data.get("host") or entry.data.get("Host")
    port = entry.data.get("port") or entry.data.get("Port", 80)
    
    hass.data[DOMAIN][entry.entry_id] = {"host": host, "port": port}

    # 2. The Traffic Controller
    async def status_message_received(msg):
        try:
            payload = json.loads(msg.payload)
            registry = er.async_get(hass)

            for obj in payload.get("objects", []):
                for device in obj.get("data", []):
                    dev_hash = device.get("hash")
                    state = device.get("states", {}).get("OnOff", {}).get("on")
                    device_type = device.get("type")
                    if device_type == "SWITCH":
                        if not dev_hash:
                            continue

                        unique_id = f"lumi_switch_{dev_hash}"

                        # Check if this unique_id exists anywhere in the registry
                        if registry.async_get_entity_id("switch", DOMAIN, unique_id) is None:
                            # It's a new device! Signal switch.py to create it.
                            _LOGGER.info("Discovered new device: %s", dev_hash)
                            dispatcher_send(hass, DISCOVERY_SIGNAL, dev_hash)

                        # State Logic: Always update the state if we have it
                        if state is not None:
                            dispatcher_send(hass, f"{DOMAIN}_state_update_{dev_hash}", state)
                    else:
                        pass # TODO: add more support for devices other than switches                     
        except Exception as e:
            _LOGGER.error("Error parsing status: %s", e)

    # 3. Subscribe once to MQTT status topic
    await mqtt.async_subscribe(hass, "component/dnet-relay/in/status", status_message_received)

    # 4. CRITICAL: Register the update listener so mDNS IP updates trigger a seamless reload
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    # 5. Single setup forward for switch platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry updates (e.g. mDNS updating the IP address)."""
    _LOGGER.info("Config entry updated, reloading Lumi integration...")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry cleanly."""
    # Unload platforms (switches)
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Clean up runtime data storage
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok