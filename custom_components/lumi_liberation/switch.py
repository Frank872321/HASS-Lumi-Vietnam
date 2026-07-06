import json
from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity
from . import DOMAIN, DISCOVERY_SIGNAL
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the switch platform."""
    
    @callback
    def add_new_switch(dev_hash):
        # We define a helper to instantiate the class
        new_switch = LumiSwitch(hass, f"Lumi Switch {dev_hash}", dev_hash)
        async_add_entities([new_switch], True)

    # 1. Listen for NEW devices discovered during runtime
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
        # IMPORTANT: This unique_id must NEVER change or you'll get duplicate entities
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