import json
from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN, DISCOVERY_SIGNAL
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_registry import async_get, async_entries_for_config_entry
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
        # Data is {"hash": dev_hash, "name": dev_name}
        new_switch = LumiSwitch(hass, data["name"], data["hash"])
        async_add_entities([new_switch], True)

    async_dispatcher_connect(hass, DISCOVERY_SIGNAL, add_new_switch)

    # 2. LOAD EXISTING DEVICES from registry on restart
    from homeassistant.helpers import entity_registry
    er = entity_registry.async_get(hass)
    
    # Get all entities that belong to this config entry
    entities = [
        entry for entry in er.entities.values() 
        if entry.config_entry_id == entry.entry_id
    ]
    
    # Tell them to exist
    for entity in entities:
        # Re-instantiate based on the unique_id we stored
        add_new_switch(entity.unique_id.replace("lumi_switch_", ""))
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