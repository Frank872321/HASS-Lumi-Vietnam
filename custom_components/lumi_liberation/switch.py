import json
from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN, DISCOVERY_SIGNAL
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_registry import async_get, async_entries_for_config_entry
import homeasssistant.helpers.entity_registry 
async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the switch platform."""
    # 1. Look up all entities that are already registered to this integration
    # Use a helper to ensure the registry is ready
    registry = async_get(hass)
    # 1. ADD EXISTING DEVICES
    # Get all entries for this specific config entry
    entities_to_add = []
    for entity_entry in async_entries_for_config_entry(registry, entry.entry_id):
        # We need the unique_id back to extract the hash
        # Assuming unique_id is: "lumi_switch_{dev_hash}"
        dev_hash = entity_entry.unique_id.replace("lumi_switch_", "")
        
        # Instantiate your switch
        new_switch = LumiSwitch(hass, entity_entry.original_name, dev_hash)
        entities_to_add.append(new_switch)
    
    if entities_to_add:
        async_add_entities(entities_to_add, True)

    # 2. DISPATCHER FOR NEW DEVICES
    @callback
    def add_new_switch(data):
        # If data is a tuple like ('hash_string',), dev_hash becomes the first item
        # If data is just a string, dev_hash becomes the string itself
        dev_hash = data[0] if isinstance(data, (list, tuple)) else data
        
        # Now dev_hash is defined in this scope, so this won't crash
        name = f"Lumi Switch {dev_hash}"
        
        # Create the entity
        new_switch = LumiSwitch(hass, name, dev_hash)
        
        # Add it to HA
        async_add_entities([new_switch], True)
    registry = async_get(hass)
    entities_to_add = []
    
    # This function automatically filters for ONLY entities belonging to THIS config entry
    for entity_entry in async_entries_for_config_entry(registry, entry.entry_id):
        # Since these are already filtered, you can trust they belong to this hub!
        
        # We need to extract the hash. 
        # If your unique_id is "lumi_switch_{dev_hash}", this works:
        dev_hash = entity_entry.unique_id.replace("lumi_switch_", "")
        
        # Instantiate your switch
        new_switch = LumiSwitch(hass, entity_entry.original_name, dev_hash)
        entities_to_add.append(new_switch)
    
    if entities_to_add:
        async_add_entities(entities_to_add, True)
class LumiSwitch(SwitchEntity):
    def __init__(self, hass, name, devid):
        self.hass = hass
        self._attr_name = name
        self._attr_unique_id = f"lumi_switch_{devid}" 
        self._devid = devid
        self._attr_is_on = False
        
    @property
    def device_info(self):
        """Link to parent device (The Hub Box)"""
        # Split MAC from the endpoint ID
        mac = "-".join(self._devid.split("-")[:-1])
        return {
            "identifiers": {(DOMAIN, mac)},
            "name": f"Lumi Hub {mac[-4:]}",
            "manufacturer": "Lumi",
        }
    async def async_turn_on(self, **kwargs):
        # Your reverse-engineered command payload
        payload = {
            "cmd": "set","control_source": {"id": "ha-dev", "type": "app"},
            "objects": [{"data": [self._devid], "execution": {"command": "OnOff", "params": {"on": True}}, "type":"devices"}],
            "reqid": "ha-dev",
            "source":"core",
            "timestamp": 0,
        }
        await mqtt.async_publish(self.hass, "component/hc-zb/control", json.dumps(payload))
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        payload = {
            "cmd": "set",
            "control_source": {"id": "ha-dev", "type": "app"},
            "objects": [{"data": [self._devid], "execution": {"command": "OnOff", "params": {"on": False}}, "type":"devices"}],
            "reqid": "ha-dev",
            "source":"core",
            "timestamp": 0,
        }
        await mqtt.async_publish(self.hass, "component/hc-zb/control", json.dumps(payload))
        self._attr_is_on = False
    async def async_added_to_hass(self):
        # Register the listener for the specific signal: {DOMAIN}_state_update_{zigbee-84...}
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, 
                f"{DOMAIN}_state_update_{self._devid}", 
                self._handle_state_update
            )
        )

    @callback
    def _handle_state_update(self, new_state):
        """Update state when the central dispatcher signals us."""
        self._attr_is_on = new_state
        self.async_write_ha_state()