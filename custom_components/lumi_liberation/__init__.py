from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, DISCOVERY_SIGNAL
import json
import logging
from homeassistant.components import mqtt
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers import entity_registry as er
_LOGGER = logging.getLogger(__name__)
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # 1. Setup Data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"host": entry.data["Host"], "port": entry.data["Port"]}

    # 2. The Traffic Controller
    async def status_message_received(msg):
        try:
            payload = json.loads(msg.payload)
            registry = er.async_get(hass)

            for obj in payload.get("objects", []):
                for device in obj.get("data", []):
                    dev_hash = device.get("hash")
                    state = device.get("states", {}).get("OnOff", {}).get("on")
                    
                    if not dev_hash:
                        continue

                    # 1. DISCOVERY LOGIC: Check if we have seen this switch before
                    # We search for an entity with the unique_id: "lumi_switch_{dev_hash}"
                    entity_id = registry.async_get_entity_id("switch", DOMAIN, f"lumi_switch_{dev_hash}")
                    
                    unique_id = f"lumi_switch_{dev_hash}"

                    # Check if this unique_id exists anywhere in the registry
                    if registry.async_get_entity_id("switch", DOMAIN, unique_id) is None:
                        # It's a new device! Signal switch.py to create it.
                        _LOGGER.info(f"Discovered new device: {dev_hash}")
                        dispatcher_send(hass, DISCOVERY_SIGNAL, dev_hash)

                    # 2. STATE LOGIC: Always update the state if we have it
                    if state is not None:
                        dispatcher_send(hass, f"{DOMAIN}_state_update_{dev_hash}", state)                       
        except Exception as e:
            _LOGGER.error(f"Error parsing status: {e}")

    # 3. Subscribe once
    await mqtt.async_subscribe(hass, "component/dnet-relay/in/status", status_message_received)

    # 4. Single setup forward
    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    return True